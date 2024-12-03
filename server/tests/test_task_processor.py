import os
import json
import time
import shutil
from models.task import Task, TaskStatus, TaskProgress
from services.task.processor import TaskProcessor
from core.config import settings
def test_task_step_retry(db_session, test_user):
    """测试任务步骤重试"""
    # 创建测试任务
    task = Task(
        taskId="test-retry-task",
        url="https://example.com/article",
        status=TaskStatus.FAILED.value,
        progress=TaskProgress.FAILED.value,
        progress_message="翻译对话内容失败",
        current_step="翻译对话内容",
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    # 创建测试文件
    processor = TaskProcessor(task, db_session, is_retry=True)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建测试内容文件
    content_filename = f"{task.taskId}_content.json"
    content_path = os.path.join(processor.temp_dir, content_filename)
    with open(content_path, 'w', encoding='utf-8') as f:
        json.dump({
            "content": "测试内容",
            "title": "测试标题"
        }, f, ensure_ascii=False, indent=2)
    
    # 创建测试对话文件
    dialogue_filename = f"{task.taskId}_cn.json"
    dialogue_path = os.path.join(processor.temp_dir, dialogue_filename)
    dialogue_cn = [
        {
            "role": "host",
            "content": "测试对话内容",
            "timestamp": [0, 1000]
        }
    ]
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue_cn, f, ensure_ascii=False, indent=2)
    
    # 通过 context_manager 设置文件路径
    processor.context_manager.set("content.json", content_filename)
    processor.context_manager.set("dialogue_cn.json", dialogue_filename)
    processor.context_manager.set("current_step_index", 2)
    
    # 保存上下文
    processor.context_manager.save()
    
    # 执行任务
    processor.process_task()
    
    # 刷新任务状态
    db_session.refresh(task)
    
    # 验证任务状态
    assert task.status == TaskStatus.COMPLETED.value
    assert task.progress == TaskProgress.COMPLETED.value
    assert task.current_step is not None
    assert task.step_progress == 100
    assert task.progress_message is not None
    assert "执行完成" in task.progress_message
    
    # 验证生成的文件
    assert os.path.exists(os.path.join(processor.temp_dir, f"{task.taskId}_en.json"))
    
    # 从文件读取翻译结果进行验证
    dialogue_en_path = os.path.join(processor.temp_dir, f"{task.taskId}_en.json")
    with open(dialogue_en_path, 'r', encoding='utf-8') as f:
        dialogue_en = json.load(f)
        
    assert dialogue_en is not None
    assert len(dialogue_en) == len(dialogue_cn)
    
    # 验证上下文
    saved_context = processor.context_manager.get_all()
    print("保存的上下文内容:", json.dumps(saved_context, ensure_ascii=False, indent=2))
    
    # 验证翻译结果文件名存在于上下文中
    assert "dialogue_en.json" in saved_context

def test_complete_task_execution(client, test_user, db_session):
    """测试完整的任务执行流程"""
    # 1. 登录获取token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpass"
        }
    )
    token = login_response.json()["access_token"]
    
    # 2. 创建任务
    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "url": "https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
            "is_public": True
        }
    )
    
    assert response.status_code == 201
    task_data = response.json()
    task_id = task_data["taskId"]
    
    # 3. 等待任务处理完成(最多等待5分钟)
    max_retries = 180
    retry_interval = 5
    task_completed = False
    
    for _ in range(max_retries):
        status_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert status_response.status_code == 200
        current_status = status_response.json()
        
        # 打印更详细的状态信息
        print(f"Current task status: {current_status}")
        print(f"Current step: {current_status.get('current_step')}")
        print(f"Progress message: {current_status.get('progress_message')}")
        
        if current_status["status"] == "completed":
            task_completed = True
            # 增加等待时间确保文件写入完成
            time.sleep(5)
            break
        elif current_status["status"] == "failed":
            error_msg = current_status.get('progress_message', '未知错误')
            print(f"Task failed: {error_msg}")
            raise AssertionError(f"任务执行失败: {error_msg}")
            
        time.sleep(retry_interval)
    
    assert task_completed, "任务未在预期时间内完成"
    
    # 验证任务结果
    task = db_session.query(Task).filter(Task.taskId == task_id).first()
    assert task is not None
    assert task.status == TaskStatus.COMPLETED.value
    assert task.progress == TaskProgress.COMPLETED.value
    
    # 验证生成的文件
    task_dir = os.path.join(settings.TASK_DIR, task_id)
    assert os.path.exists(task_dir), f"任务目录不存在: {task_dir}"
    
    # 打印目录内容用于调试
    print("Task directory contents:")
    for root, dirs, files in os.walk(task_dir):
        for file in files:
            print(f"- {file}")
    
    # 验证音频文件
    cn_audio = os.path.join(task_dir, f"{task_id}_cn.mp3")
    en_audio = os.path.join(task_dir, f"{task_id}_en.mp3")
    assert os.path.exists(cn_audio), f"中文音频文件不存在: {cn_audio}"
    assert os.path.exists(en_audio), f"英文音频文件不存在: {en_audio}"
    
    # 验证字幕文件
    assert os.path.exists(os.path.join(task_dir, f"{task_id}_cn.srt"))
    assert os.path.exists(os.path.join(task_dir, f"{task_id}_en.srt"))
    
    # 清理测试文件
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)

def test_task_execution_failure(db_session, test_user):
    """测试任务执行失败场景"""
    # 创建测试任务
    task = Task(
        taskId="test-failure-task",
        url="https://invalid-url.com",  # 使用合法但无效的URL
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.WAITING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    # 创建处理器并执行任务
    processor = TaskProcessor(task, db_session)
    
    # 执行任务并捕获异常
    try:
        processor.process_task()
    except Exception:
        pass  # 我们期望任务失败，所以忽略异常
        
    # 验证任务状态
    db_session.refresh(task)
    
    # 验证任务失败状态
    assert task.status == TaskStatus.FAILED.value
    assert task.progress == TaskProgress.FAILED.value
    assert task.current_step == "获取页面内容"
    assert task.step_progress == 0
    assert task.progress_message is not None
    assert "请求URL失败" in task.progress_message
    
    # 验证上下文是否保存
    context_file = os.path.join(processor.temp_dir, "context.json")
    assert os.path.exists(context_file)
    
    # 验证上下文内容
    with open(context_file, 'r', encoding='utf-8') as f:
        context = json.load(f)
        assert context['taskId'] == task.taskId
        assert context['status'] == TaskStatus.FAILED.value
    
    # 清理测试文件
    if os.path.exists(processor.temp_dir):
        shutil.rmtree(processor.temp_dir)