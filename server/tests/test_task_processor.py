import os
import json
import time
import shutil
from unittest.mock import patch, MagicMock
from models.task import Task, TaskStatus, TaskProgress
from services.task.processor import TaskProcessor
from core.config import settings
from services.task.steps.content import ContentStep
from services.task.steps.fetch_content import FetchContentStep
from services.task.steps.generate_title import GenerateTitleStep
from services.task.steps.dialogue import DialogueStep
from services.task.steps.translation import TranslationStep
from services.task.steps.audio import AudioStep


def test_fetch_content_step(db_session, test_user):
    """测试内容获取步骤"""
    task = Task(
        taskId="test-fetch-content",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 设置上下文
    processor.context_manager.set("url", task.url)
    processor.context_manager.set("taskId", task.taskId)
    processor.context_manager.set("current_step_index", 0)
    
    fetch_content_step = FetchContentStep(
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行内容获取步骤
        result = fetch_content_step.execute()
        
        # 验证结果
        assert "raw_content.txt" in result  # 改为.txt
        assert "raw_content" in result
        
        # 验证生成的文件
        content_filename = result["raw_content.txt"]
        content_path = os.path.join(processor.temp_dir, content_filename)
        assert os.path.exists(content_path)
        
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()  # 直接读取文本内容
            assert len(content) > 0
            
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def mock_generate_title(*args, **kwargs):
    """模拟标题生成"""
    return "文字的迷宫，意义的探寻"

@patch('services.task.steps.generate_title.GenerateTitleStep._generate_title', side_effect=mock_generate_title)
def test_generate_title_step(mock_generate_title, db_session, test_user):
    """测试标题生成步骤"""
    task = Task(
        taskId="test-generate-title",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建raw_content.txt
    raw_content = "这是一篇测试文章的内容..."
    raw_content_filename = "raw_content.txt"
    raw_content_path = os.path.join(processor.temp_dir, raw_content_filename)
    with open(raw_content_path, 'w', encoding='utf-8') as f:
        f.write(raw_content)
    
    # 设置上下文
    processor.context_manager.set("raw_content.txt", raw_content_filename)
    processor.context_manager.set("raw_content", raw_content)
    processor.context_manager.set("taskId", task.taskId)
    processor.context_manager.set("current_step_index", 1)
    
    generate_title_step = GenerateTitleStep(
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行标题生成步骤
        result = generate_title_step.execute()
        
        # 验证结果
        assert "title" in result
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 0
            
        # 验证任务标题已更新
        db_session.refresh(task)
        assert task.title == result["title"]
            
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def test_content_step(db_session, test_user):
    """测试内容处理步骤"""
    task = Task(
        taskId="test-content-step",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建难度等级目录
    level = "elementary"
    level_dir = os.path.join(processor.temp_dir, level)
    os.makedirs(level_dir, exist_ok=True)
    
    # 创建raw_content.txt
    raw_content = "这是一篇测试文章的内容..."  # 直接使用文本内容
    raw_content_filename = "raw_content.txt"
    raw_content_path = os.path.join(processor.temp_dir, raw_content_filename)
    with open(raw_content_path, 'w', encoding='utf-8') as f:
        f.write(raw_content)  # 直接写入文本
        
    # 创建title.txt
    title = "测试标题"  # 直接使用文本内容
    title_filename = "title.txt"
    title_path = os.path.join(processor.temp_dir, title_filename)
    with open(title_path, 'w', encoding='utf-8') as f:
        f.write(title)  # 直接写入文本
    
    # 设置上下文
    processor.context_manager.set("raw_content.txt", raw_content_filename)
    processor.context_manager.set("raw_content", raw_content)
    processor.context_manager.set("title.txt", title_filename)
    processor.context_manager.set("title", title)
    processor.context_manager.set("level_dir", level_dir)
    processor.context_manager.set("current_step_index", 2)
    
    content_step = ContentStep(
        level="elementary",
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行内容处理步骤
        result = content_step.execute()
        
        # 验证结果
        assert f"{level}/content.txt" in result  # 改为.txt
        
        # 验证生成的文件
        content_filename = result[f"{level}/content.txt"]
        content_path = os.path.join(level_dir, content_filename)
        assert os.path.exists(content_path)
        
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()  # 直接读取文本内容
            assert len(content) > 0
            
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def test_dialogue_step(db_session, test_user):
    """测试对话生成步骤"""
    task = Task(
        taskId="test-dialogue-step",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建难度等级目录
    level = "elementary"
    level_dir = os.path.join(processor.temp_dir, level)
    os.makedirs(level_dir, exist_ok=True)
    
    # 设置上下文
    processor.context_manager.set("level_dir", level_dir)
    processor.context_manager.set("current_step_index", 0)
    processor.context_manager.set("current_level", "elementary")
    processor.context_manager.set("role", "host")
    processor.context_manager.set("style_params", {
        "role": "host",
        "tone": "friendly",
        "length": "medium"
    })
    
    # 修改内容文件的存放位置和设置
    content_data = "This is test content..."  # 改为纯文本内容
    content_filename = "content.txt"  # 改为.txt
    content_path = os.path.join(level_dir, content_filename)
    with open(content_path, 'w', encoding='utf-8') as f:
        f.write(content_data)
        
    # 更新上下文中的文件路径
    processor.context_manager.set(f"{level}/content.txt", content_filename)
        
    dialogue_step = DialogueStep(
        level="elementary",
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行对话生成步骤
        result = dialogue_step.execute()
        
        # 验证结果
        assert f"{level}/dialogue_en.json" in result  # 改为检查英文对话文件
        
        # 验证生成的文件
        dialogue_filename = result[f"{level}/dialogue_en.json"]  # 改为英文对话文件名
        dialogue_path = os.path.join(level_dir, dialogue_filename)
        assert os.path.exists(dialogue_path)
        
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue_data = json.load(f)
            assert isinstance(dialogue_data, list)
            assert len(dialogue_data) > 0
            for item in dialogue_data:
                assert "role" in item
                assert "content" in item
                assert item["role"] in ["host", "guest"]
                # 可以添加检查确保内容是英文的逻辑
                assert isinstance(item["content"], str)
                assert len(item["content"]) > 0
                
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def test_translation_step(db_session, test_user):
    """测试翻译步骤"""
    task = Task(
        taskId="test-translation-step",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建难度等级目录
    level = "elementary"
    level_dir = os.path.join(processor.temp_dir, level)
    os.makedirs(level_dir, exist_ok=True)
    
    # 设置level_dir到上下文
    processor.context_manager.set("level_dir", level_dir)
    processor.context_manager.set("current_step_index", 0)  # 添加步骤索引
    
    # 创建测试英文对话文件
    dialogue_en = [
        {
            "role": "host",
            "content": "Hello, welcome to our show"
        },
        {
            "role": "guest",
            "content": "Thank you, glad to be here"
        }
    ]
    dialogue_filename = "dialogue_en.json"
    dialogue_path = os.path.join(level_dir, dialogue_filename)
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue_en, f, ensure_ascii=False, indent=2)
        
    processor.context_manager.set(f"{level}/dialogue_en.json", dialogue_filename)
    translation_step = TranslationStep(
        level="elementary",
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行翻译步骤
        result = translation_step.execute()
        
        # 验证结果
        assert f"{level}/dialogue_cn.json" in result
        
        # 验证生成的文件
        dialogue_filename = result[f"{level}/dialogue_cn.json"]
        dialogue_path = os.path.join(level_dir, dialogue_filename)
        assert os.path.exists(dialogue_path)
        
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue_cn = json.load(f)
            assert isinstance(dialogue_cn, list)
            assert len(dialogue_cn) == len(dialogue_en)
            for item in dialogue_cn:
                assert "role" in item
                assert "content" in item
                assert item["role"] in ["host", "guest"]
                # 可以添加检查确保内容是中文的逻辑
                assert isinstance(item["content"], str)
                assert len(item["content"]) > 0
                
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def test_audio_step(db_session, test_user):
    """测试音频生成步骤"""
    task = Task(
        taskId="test-audio-step",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False
    )
    db_session.add(task)
    db_session.commit()
    
    processor = TaskProcessor(task, db_session)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建难度等级目录
    level = "elementary"
    lang = "cn"
    level_dir = os.path.join(processor.temp_dir, level)
    os.makedirs(level_dir, exist_ok=True)
    
    # 设置level_dir到上下文
    processor.context_manager.set("level_dir", level_dir)
    processor.context_manager.set("current_step_index", 0)  # 添加步骤索引
    
    # 创建测试对话文件
    dialogue = [
        {
            "role": "host",
            "content": "你好，欢迎收听"
        },
        {
            "role": "guest",
            "content": "谢谢，很高兴参与讨论"
        }
    ]
    dialogue_filename = f"{task.taskId}_{level}_cn.json"
    dialogue_path = os.path.join(level_dir, dialogue_filename)
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue, f, ensure_ascii=False, indent=2)
        
    processor.context_manager.set(f"{level}/dialogue_cn.json", dialogue_filename)
    audio_step = AudioStep(
        level="elementary",
        lang="cn",
        progress_tracker=processor.progress_tracker,
        context_manager=processor.context_manager
    )
    
    try:
        # 执行音频生成步骤
        result = audio_step.execute()
        
        # 验证结果
        assert f"{level}/audio_files_{lang}.json" in result  # 修改这里
        
        # 验证生成的文件
        audio_files_filename = result[f"{level}/audio_files_{lang}.json"]  # 改这里
        audio_files_path = os.path.join(level_dir, audio_files_filename)
        assert os.path.exists(audio_files_path)
        
        with open(audio_files_path, 'r', encoding='utf-8') as f:
            audio_files = json.load(f)
            assert isinstance(audio_files, list)
            assert len(audio_files) == len(dialogue)
            for item in audio_files:
                assert "index" in item
                assert "role" in item
                assert "filename" in item
                audio_path = os.path.join(level_dir, item["filename"])
                assert os.path.exists(audio_path)
                
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

def test_task_step_retry(db_session, test_user):
    """测试任务步骤重试"""
    # 设置mock的返回值
    mock_audio_segment = MagicMock()
    mock_audio_segment.duration_seconds = 5.0
    mock_audio_segment.__len__ = lambda self: 5000  # 添加这行，模拟5秒长度
    mock_audio_segment.__add__ = lambda self, other: mock_audio_segment
    mock_audio_segment.export = MagicMock()
    mock_audio_segment.set_frame_rate = MagicMock(return_value=mock_audio_segment)
    mock_audio_segment.set_channels = MagicMock(return_value=mock_audio_segment)
    
    # 设置所有mock的返回值
    mock_subtitle_from_mp3 = MagicMock(return_value=mock_audio_segment)
    mock_merge_from_mp3 = MagicMock(return_value=mock_audio_segment)
    mock_merge_from_file = MagicMock(return_value=mock_audio_segment)
    mock_verify_audio = MagicMock(return_value=True)  # 添加这行，保验证总是通过
    
    task = Task(
        taskId="test-retry-task",
        url="https://mp.weixin.qq.com/s/oPu6ngqcN2fNHdvP-dW-AQ",
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
    
    processor = TaskProcessor(task, db_session, is_retry=True)
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 为每个难度等级创建目录和文件
    levels = ["elementary", "intermediate", "advanced"]
    for level in levels:
        level_dir = os.path.join(processor.temp_dir, level)
        os.makedirs(level_dir, exist_ok=True)
        
        # 设置上下文
        processor.context_manager.set("level_dir", level_dir)
        processor.context_manager.set("current_level", level)
        processor.context_manager.set("style_params", {  # 添加风格参数
            "role": "host",
            "tone": "friendly",
            "length": "medium"
        })
        
        # 创建内容文件
        content_data = "This is test content..."
        content_filename = "content.txt"
        content_path = os.path.join(level_dir, content_filename)
        with open(content_path, 'w', encoding='utf-8') as f:
            f.write(content_data)
            
        processor.context_manager.set(f"{level}/content.txt", content_filename)
            
        # 修改对话文件创建部分
        dialogue_en = [
            {
                "role": "host",
                "content": "Let's discuss the importance of educational innovation"
            },
            {
                "role": "guest", 
                "content": "Educational innovation is indeed an important topic"
            }
        ]
        dialogue_filename = "dialogue_en.json"  # 改为en
        dialogue_path = os.path.join(level_dir, dialogue_filename)
        with open(dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_en, f, ensure_ascii=False, indent=2)
            
        # 创建中文对话文件
        dialogue_cn = [
            {
                "role": "host",
                "content": "让我们来讨论教育创新的重要性"
            },
            {
                "role": "guest", 
                "content": "教育创新确实是当今社会发展的重要议题"
            }
        ]
        dialogue_cn_filename = "dialogue_cn.json"
        dialogue_cn_path = os.path.join(level_dir, dialogue_cn_filename)
        with open(dialogue_cn_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_cn, f, ensure_ascii=False, indent=2)
            
        # 创建音频文件配置
        audio_files_cn = [
            {
                "index": 0,
                "role": "host",
                "filename": "0000_cn_host.mp3",
                "text": "让我们来讨论下教育创新的重要性"
            },
            {
                "index": 1,
                "role": "guest",
                "filename": "0001_cn_guest.mp3",
                "text": "教育创新确实是当今社会发展的重要议题"
            }
        ]
        
        audio_files_en = [
            {
                "index": 0,
                "role": "host",
                "filename": "0000_en_host.mp3",
                "text": "Let's discuss the importance of educational innovation"
            },
            {
                "index": 1,
                "role": "guest",
                "filename": "0001_en_guest.mp3",
                "text": "Educational innovation is indeed an important topic"
            }
        ]
        
        # 保存音频配置文件
        audio_config_cn_filename = "audio_files_cn.json"
        audio_config_cn_path = os.path.join(level_dir, audio_config_cn_filename)
        with open(audio_config_cn_path, 'w', encoding='utf-8') as f:
            json.dump(audio_files_cn, f, ensure_ascii=False, indent=2)
            
        audio_config_en_filename = "audio_files_en.json"
        audio_config_en_path = os.path.join(level_dir, audio_config_en_filename)
        with open(audio_config_en_path, 'w', encoding='utf-8') as f:
            json.dump(audio_files_en, f, ensure_ascii=False, indent=2)
            
        # 更新上下文
        processor.context_manager.set(f"{level}/dialogue_en.json", dialogue_filename)
        processor.context_manager.set(f"{level}/dialogue_cn.json", dialogue_cn_filename)
        processor.context_manager.set(f"{level}/audio_files_cn.json", audio_config_cn_filename)
        processor.context_manager.set(f"{level}/audio_files_en.json", audio_config_en_filename)
        processor.context_manager.set(f"{level}_dir", level_dir)
        
        # 创建模拟的音频文件
        for audio in audio_files_cn + audio_files_en:
            audio_path = os.path.join(level_dir, audio["filename"])
            with open(audio_path, 'wb') as f:
                f.write(b'\xFF\xFB\x30\x00')  # MP3 文件头
                for _ in range(10):
                    f.write(b'\xFF\xFB\x30\x00' + b'\x00' * 380)
    
    # 修改 mock 返回值以支持多个难度等级
    with patch('services.task.steps.audio.AudioStep._generate_audio_with_retry') as mock_generate_audio, \
         patch('services.task.steps.audio.EdgeTTSService', return_value=MagicMock()), \
         patch('services.task.steps.audio.AudioSegment.from_mp3', return_value=mock_audio_segment), \
         patch('services.task.steps.audio.AudioSegment.from_file', return_value=mock_audio_segment), \
         patch('services.task.steps.dialogue.DialogueStep._execute') as mock_dialogue, \
         patch('services.task.steps.translation.TranslationStep._execute') as mock_translate, \
         patch('services.task.steps.audio.AudioStep._verify_audio_file', return_value=True) as mock_verify_audio:
        
        # 在测试函数中更新mock的side_effect
        mock_dialogue.side_effect = mock_dialogue_execute
        mock_translate.side_effect = mock_translate_execute
        mock_generate_audio.return_value = True
        
        try:
            processor.process_task()
            
            # 验证任务状态
            db_session.refresh(task)
            assert task.status == TaskStatus.COMPLETED.value  # 确保任务完成
            assert task.progress == TaskProgress.COMPLETED.value
            
            # 验证生成的文件
            for level in levels:
                level_dir = os.path.join(processor.temp_dir, level)
                assert os.path.exists(os.path.join(level_dir, "content.txt"))
                assert os.path.exists(os.path.join(level_dir, "dialogue_en.json"))
                assert os.path.exists(os.path.join(level_dir, "dialogue_cn.json"))
            
        finally:
            if os.path.exists(processor.temp_dir):
                shutil.rmtree(processor.temp_dir)
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

def setup_test_files_and_dirs(processor, task, levels=None):
    """设置测试文件和目录的辅助函数"""
    if levels is None:
        levels = ["elementary", "intermediate", "advanced"]
        
    os.makedirs(processor.temp_dir, exist_ok=True)
    
    # 创建raw_content.txt
    raw_content = "这是一篇测试文章的内容..."
    raw_content_filename = "raw_content.txt"  # 改为.txt
    raw_content_path = os.path.join(processor.temp_dir, raw_content_filename)
    with open(raw_content_path, 'w', encoding='utf-8') as f:
        f.write(raw_content)  # 直接写入文本
    
    # 创建title.txt
    title = "测试标题"
    title_filename = "title.txt"  # 改为.txt
    title_path = os.path.join(processor.temp_dir, title_filename)
    with open(title_path, 'w', encoding='utf-8') as f:
        f.write(title)  # 直接写入文本
    
    # 为每个难度等级创建目录和文件
    for level in levels:
        level_dir = os.path.join(processor.temp_dir, level)
        os.makedirs(level_dir, exist_ok=True)
        
        # 创建对话文件
        dialogue_cn = [
            {
                "role": "host",
                "content": "让我们来讨论下教育创新的重要性"
            },
            {
                "role": "guest", 
                "content": "教育创新确实是当今社会发展的重要议题"
            }
        ]
        dialogue_filename = "dialogue_cn.json"
        dialogue_path = os.path.join(level_dir, dialogue_filename)
        with open(dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_cn, f, ensure_ascii=False, indent=2)
            
        # 创建英文对话文件
        dialogue_en = [
            {
                "role": "host",
                "content": "Let's discuss the importance of educational innovation"
            },
            {
                "role": "guest", 
                "content": "Educational innovation is indeed an important topic"
            }
        ]
        dialogue_en_filename = "dialogue_en.json"
        dialogue_en_path = os.path.join(level_dir, dialogue_en_filename)
        with open(dialogue_en_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_en, f, ensure_ascii=False, indent=2)
            
        # 创建音频文件配置
        audio_files_cn = [
            {
                "index": 0,
                "role": "host",
                "filename": "0000_cn_host.mp3",
                "text": "让我们来讨论下教育创新的重要性"
            },
            {
                "index": 1,
                "role": "guest",
                "filename": "0001_cn_guest.mp3",
                "text": "教育创新确实是当今社会发展的重要议题"
            }
        ]
        
        audio_files_en = [
            {
                "index": 0,
                "role": "host",
                "filename": "0000_en_host.mp3",
                "text": "Let's discuss the importance of educational innovation"
            },
            {
                "index": 1,
                "role": "guest",
                "filename": "0001_en_guest.mp3",
                "text": "Educational innovation is indeed an important topic"
            }
        ]
        
        # 保存音频配置文件
        audio_config_cn_filename = "audio_files_cn.json"
        audio_config_cn_path = os.path.join(level_dir, audio_config_cn_filename)
        with open(audio_config_cn_path, 'w', encoding='utf-8') as f:
            json.dump(audio_files_cn, f, ensure_ascii=False, indent=2)
            
        audio_config_en_filename = "audio_files_en.json"
        audio_config_en_path = os.path.join(level_dir, audio_config_en_filename)
        with open(audio_config_en_path, 'w', encoding='utf-8') as f:
            json.dump(audio_files_en, f, ensure_ascii=False, indent=2)
            
        # 更新上下文
        processor.context_manager.set(f"{level}/dialogue_cn.json", dialogue_filename)
        processor.context_manager.set(f"{level}/dialogue_en.json", dialogue_en_filename)
        processor.context_manager.set(f"{level}/audio_files_cn.json", audio_config_cn_filename)
        processor.context_manager.set(f"{level}/audio_files_en.json", audio_config_en_filename)
        processor.context_manager.set(f"{level}_dir", level_dir)
        
        # 创建模拟的音频文件
        for audio in audio_files_cn + audio_files_en:
            audio_path = os.path.join(level_dir, audio["filename"])
            with open(audio_path, 'wb') as f:
                f.write(b'\xFF\xFB\x30\x00')  # MP3 文件头
                for _ in range(10):
                    f.write(b'\xFF\xFB\x30\x00' + b'\x00' * 380)
    
    # 设置基本上下文
    processor.context_manager.set("raw_content.txt", raw_content_filename)
    processor.context_manager.set("raw_content", raw_content)
    processor.context_manager.set("title.txt", title_filename)
    processor.context_manager.set("title", title)

@patch('services.task.steps.audio.AudioSegment.from_mp3')
@patch('services.task.steps.audio.AudioSegment.from_file')
@patch('services.task.steps.audio.AudioStep._verify_audio_file')
@patch('services.task.steps.audio.EdgeTTSService')
@patch('services.task.steps.audio.AudioStep._generate_audio_with_retry')
@patch('services.task.steps.dialogue.DialogueStep._execute')
@patch('services.task.steps.translation.TranslationStep._execute')
def test_dialogue_generation_with_difficulty_levels(
    mock_translate, mock_dialogue, mock_generate_audio, 
    mock_tts_service, mock_verify_audio, mock_from_file, mock_from_mp3,
    db_session, test_user):
    """测试不同难度等级的对话生成"""
    # 设置mock返回值
    mock_audio_segment = MagicMock()
    mock_audio_segment.duration_seconds = 5.0
    mock_audio_segment.__len__ = lambda self: 5000  # 添加这行，模拟5秒长度
    mock_audio_segment.__add__ = lambda self, other: mock_audio_segment
    mock_audio_segment.export = MagicMock()
    mock_audio_segment.set_frame_rate = MagicMock(return_value=mock_audio_segment)
    mock_audio_segment.set_channels = MagicMock(return_value=mock_audio_segment)
    
    mock_verify_audio.return_value = True
    mock_generate_audio.return_value = True
    mock_tts_service.return_value = MagicMock()
    mock_dialogue.side_effect = mock_dialogue_execute
    mock_translate.side_effect = mock_translate_execute
    mock_from_file.return_value = mock_audio_segment
    mock_from_mp3.return_value = mock_audio_segment
    
    task = Task(
        taskId="test-difficulty-levels",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False,
        metadata={
            "difficulty_level": "intermediate",
            "style_params": {
                "length": "medium", 
                "tone": "casual",
                "emotion": "positive",
                "professionalism": "moderate"
            }
        }
    )
    db_session.add(task)
    db_session.commit()

    processor = TaskProcessor(task, db_session)
    
    try:
        setup_test_files_and_dirs(processor, task)
        processor.process_task()
        
        # 验证任务状态
        db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value
        assert task.progress == TaskProgress.COMPLETED.value
        
        # 修改期望的文件结构，使用标准化的文件名格式
        expected_files = {
            'elementary': {
                'cn': {
                    'audio': f"elementary_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"elementary_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"elementary_en_audio_{task.taskId}.mp3",
                    'subtitle': f"elementary_en_subtitle_{task.taskId}.srt"
                }
            },
            'intermediate': {
                'cn': {
                    'audio': f"intermediate_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"intermediate_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"intermediate_en_audio_{task.taskId}.mp3",
                    'subtitle': f"intermediate_en_subtitle_{task.taskId}.srt"
                }
            },
            'advanced': {
                'cn': {
                    'audio': f"advanced_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"advanced_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"advanced_en_audio_{task.taskId}.mp3",
                    'subtitle': f"advanced_en_subtitle_{task.taskId}.srt"
                }
            }
        }
        
        assert task.files == expected_files
        
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

@patch('services.task.steps.audio.AudioSegment.from_mp3')
@patch('services.task.steps.audio.AudioSegment.from_file')
@patch('services.task.steps.audio.AudioStep._verify_audio_file')
@patch('services.task.steps.audio.EdgeTTSService')
@patch('services.task.steps.audio.AudioStep._generate_audio_with_retry')
@patch('services.task.steps.dialogue.DialogueStep._execute')
@patch('services.task.steps.translation.TranslationStep._execute')
def test_dialogue_generation_style_parameters(
    mock_translate, mock_dialogue, mock_generate_audio, 
    mock_tts_service, mock_verify_audio, mock_from_file, mock_from_mp3,
    db_session, test_user):
    """测试对话生成的风格参数"""
    # 设置mock返回值
    mock_audio_segment = MagicMock()
    mock_audio_segment.duration_seconds = 5.0
    mock_audio_segment.__len__ = lambda self: 5000  # 添加这行，模拟5秒长度
    mock_audio_segment.__add__ = lambda self, other: mock_audio_segment
    mock_audio_segment.export = MagicMock()
    mock_audio_segment.set_frame_rate = MagicMock(return_value=mock_audio_segment)
    mock_audio_segment.set_channels = MagicMock(return_value=mock_audio_segment)
    
    mock_verify_audio.return_value = True
    mock_generate_audio.return_value = True
    mock_tts_service.return_value = MagicMock()
    mock_dialogue.side_effect = mock_dialogue_execute
    mock_translate.side_effect = mock_translate_execute
    mock_from_file.return_value = mock_audio_segment
    mock_from_mp3.return_value = mock_audio_segment
    
    task = Task(
        taskId="test-style-params",
        url="https://mp.weixin.qq.com/s/UXb0KyDCSHkUS_4dCGlsfQ",
        status=TaskStatus.PROCESSING.value,
        progress=TaskProgress.PROCESSING.value,
        user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
        is_public=False,
        metadata={
            "difficulty_level": "advanced",
            "style_params": {
                "length": "long",
                "tone": "formal", 
                "emotion": "neutral",
                "professionalism": "expert"
            }
        }
    )
    db_session.add(task)
    db_session.commit()

    processor = TaskProcessor(task, db_session)
    
    try:
        setup_test_files_and_dirs(processor, task)
        processor.process_task()
        
        # 验证任务状态
        db_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED.value
        assert task.progress == TaskProgress.COMPLETED.value
        
        # 验证files内容，使用标准化的文件名格式
        expected_files = {
            'elementary': {
                'cn': {
                    'audio': f"elementary_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"elementary_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"elementary_en_audio_{task.taskId}.mp3",
                    'subtitle': f"elementary_en_subtitle_{task.taskId}.srt"
                }
            },
            'intermediate': {
                'cn': {
                    'audio': f"intermediate_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"intermediate_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"intermediate_en_audio_{task.taskId}.mp3",
                    'subtitle': f"intermediate_en_subtitle_{task.taskId}.srt"
                }
            },
            'advanced': {
                'cn': {
                    'audio': f"advanced_cn_audio_{task.taskId}.mp3",
                    'subtitle': f"advanced_cn_subtitle_{task.taskId}.srt"
                },
                'en': {
                    'audio': f"advanced_en_audio_{task.taskId}.mp3",
                    'subtitle': f"advanced_en_subtitle_{task.taskId}.srt"
                }
            }
        }
        
        assert task.files == expected_files
        
    finally:
        if os.path.exists(processor.temp_dir):
            shutil.rmtree(processor.temp_dir)

from unittest.mock import patch, MagicMock

# 修改mock_dialogue_execute函数
def mock_dialogue_execute(*args, **kwargs):
    """模拟对话生成"""
    context_manager = args[0]
    level = context_manager.get("current_level")
    
    if not level:
        raise ValueError("current_level not found in context")
    
    return {
        f"{level}/dialogue_en.json": "dialogue_en.json"
    }

# 修改mock_translate_execute函数
def mock_translate_execute(*args, **kwargs):
    """模拟翻译执行"""
    context_manager = args[0]
    level = context_manager.get("current_level")
    
    if not level:
        raise ValueError("current_level not found in context")
    
    return {
        f"{level}/dialogue_cn.json": "dialogue_cn.json",
        f"{level}/dialogue_en.json": "dialogue_en.json"  # 添加英文对话文件
    }
