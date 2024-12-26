import os
import json
import time
import shutil
from models.task import Task, TaskStatus, TaskProgress
from services.task.processor import TaskProcessor
from core.config import settings
from services.task.steps.content import ContentStep
from services.task.steps.dialogue import DialogueStep
from services.task.steps.translation import TranslationStep
from services.task.steps.audio import AudioStep
import tempfile
from datetime import datetime


def test_complete_task_execution(client, test_user, db_session):
    """测试完整的任务执行流程"""
    start_time = time.time()
    temp_dir = None
    try:
        # 1. 登录获取token
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpass"
            }
        )
        assert login_response.status_code == 200, f"登录失败: {login_response.text}"
        token = login_response.json()["access_token"]
        
        # 2. 创建任务
        response = client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "url": "https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
                "is_public": True,
                "style_params": {
                    "content_length": "medium",
                    "tone": "casual",
                    "emotion": "neutral"
                }
            }
        )
        
        assert response.status_code == 201, f"创建任务失败: {response.text}"
        task_data = response.json()
        task_id = task_data["taskId"]
        
        # 3. 等待任务处理完成(最多等待10分钟)
        max_retries = 120  # 120次
        retry_interval = 5  # 5秒
        task_completed = False
        
        for retry_count in range(max_retries):
            status_response = client.get(
                f"/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert status_response.status_code == 200, f"获取任务状态失败: {status_response.text}"
            current_status = status_response.json()
            
            # 添加更详细的调试信息
            print(f"Retry {retry_count + 1}/{max_retries}")
            print(f"Current task status: {current_status}")
            print(f"Current step: {current_status.get('current_step')}")
            print(f"Progress message: {current_status.get('progress_message')}")
            
            if current_status["status"] == "completed":
                task_completed = True
                break
            elif current_status["status"] == "failed":
                raise Exception(f"任务处理失败: {current_status.get('error', '未知错误')}")
            
            time.sleep(retry_interval)
        
        assert task_completed, "任务未在规定时间内完成"
        
        # 4. 验证任务结果
        final_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert final_response.status_code == 200, f"获取最终任务状态失败: {final_response.text}"
        final_task = final_response.json()
        
        # 验证任务状态
        assert final_task["status"] == "completed"
        assert final_task["progress"] == "completed"
        assert "files" in final_task
        assert isinstance(final_task["files"], dict)
        
        # 验证任务结果
        task = db_session.query(Task).filter(Task.taskId == task_id).first()
        assert task is not None
        assert task.status == TaskStatus.COMPLETED.value
        assert task.progress == TaskProgress.COMPLETED.value
        
        # 打印目录内容用于调试
        task_dir = os.path.join(settings.TASK_DIR, task_id)
        print("\nTask directory structure:")
        for root, dirs, files in os.walk(task_dir):
            level = root.replace(task_dir, '').count(os.sep)
            indent = '  ' * level
            folder = os.path.basename(root)
            print(f"{indent}+ {folder}/")
            for file in files:
                print(f"{indent}  - {file}")
                
        # 复制任务目录到临时目录
        temp_dir = tempfile.mkdtemp(prefix="task_")
        temp_task_dir = os.path.join(temp_dir, task_id)
        shutil.copytree(task_dir, temp_task_dir)
        print(f"\nTask directory copied to: {temp_task_dir}")
        
        # 验证生成的文件
        for level in task.files:
            # 验证中文文件
            cn_files = task.files[level]["cn"]
            assert os.path.exists(cn_files["audio"]), f"中文音频文件不存在: {cn_files['audio']}"
            assert os.path.exists(cn_files["subtitle"]), f"中文字幕文件不存在: {cn_files['subtitle']}"
            
            # 验证英文文件
            en_files = task.files[level]["en"]
            assert os.path.exists(en_files["audio"]), f"英文音频文件不存在: {en_files['audio']}"
            assert os.path.exists(en_files["subtitle"]), f"英文字幕文件不存在: {en_files['subtitle']}"
    
    except Exception as e:
        print(f"测试失败: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"Traceback:\n{''.join(traceback.format_tb(e.__traceback__))}")
        raise
    finally:
        # 确保清理任何剩余的资源
        try:
            if 'task_id' in locals():
                db_session.query(Task).filter(Task.taskId == task_id).delete()
                db_session.commit()
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")
            db_session.rollback()
            
        # 打印总执行时间
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\nTotal execution time: {execution_time:.2f} seconds")
