import json
import os
import re
import shutil
import threading
import time
from datetime import datetime
from functools import wraps
from pydantic import BaseModel, Field

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from pydub import AudioSegment
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from typing import List, Dict
from sqlalchemy.orm import Session
from app import models
from app.config import CONFIG
import yaml

from app.tts_handle import generate_speech

# 初始化OpenAI客户端（用于TTS）
tts_client = OpenAI(base_url=CONFIG['TTS_BASE_URL'], api_key=CONFIG['TTS_API_KEY'])

# 初始化 LangChain 的 ChatOpenAI（用于对话生成）
llm_chat = ChatOpenAI(
    model_name=CONFIG['MODEL'],
    openai_api_key=CONFIG['API_KEY'],
    openai_api_base=CONFIG['API_BASE_URL']
)

class DialogueItem(BaseModel):
    role: str = Field(description="对话角色,可以是 'host' 或 'guest'")
    content: str = Field(description="对话内容")

class DialogueOutput(BaseModel):
    dialogue: List[DialogueItem] = Field(description="对话列表")

def log(message):
    print(f"[{datetime.now().isoformat()}] {message}")

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log(f"{func.__name__} 失败: {str(e)}")
            return None
    return wrapper

@error_handler
def fetch_url_content(url, task_id):
    task_dir = os.path.join(CONFIG['TASK_DIR'], task_id)
    content_file = os.path.join(task_dir, 'content.txt')
    title_file = os.path.join(task_dir, 'title.txt')

    if os.path.exists(content_file) and os.path.getsize(content_file) > 0:
        log(f"发现已存在的内容文件: {content_file}")
        with open(content_file, 'r', encoding='utf-8') as f:
            text_content = f.read()
        log(f"已从现有文件加载内容，长度: {len(text_content)} 字符")
        
        title = "无标题"
        if os.path.exists(title_file):
            with open(title_file, 'r', encoding='utf-8') as f:
                title = f.read().strip()
    else:
        log(f"正在获取页面内容: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        os.makedirs(task_dir, exist_ok=True)
        
        with open(os.path.join(task_dir, 'old.html'), 'w', encoding='utf-8') as f:
            f.write(response.text)
        log("原始HTML已保存到old.html文件")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text().replace('\n', ' ').replace('\r', '')
        
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        log("纯文本内容已保存到content.txt文件")
        
        title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1) if title_match else ""
        
        if not title:
            if len(text_content) < 4:
                log("获取页面内容失败或内容为空，请重新提交")
                title = "获取页面内容失败或内容为空，请重新提交"
            else:
                log("标题为空，正在调用LLM生成播客标题")
                title = generate_podcast_title(text_content)
        
        with open(title_file, 'w', encoding='utf-8') as f:
            f.write(title)
        log("标题已保存到title.txt文件")
    
    log(f"成功获取页面内容，长度: {len(text_content)} 字符")
    return text_content, title

@error_handler
def generate_podcast_title(content):
    log("开始生播客标题")
    
    chat_prompt = create_chat_prompt("podcast_title_generation")
    
    chain = chat_prompt | llm_chat | StrOutputParser()
    
    for attempt in range(2):
        try:
            title = chain.invoke({"content": content})
            log(f"成功生成播客标题: {title}")
            return title.strip()
        except Exception as e:
            log(f'LLM请求失败 (尝试 {attempt+1}/2): {str(e)}')
            if attempt == 1:  # 最后一次尝试失败
                log("所有LLM请求尝试均失败，使用默认标题")
                return "无标题"

class TaskProcessor:
    def __init__(self, task: models.TaskModel, db: Session):
        self.task = task
        self.task_id = task.taskId
        self.url = task.url
        self.db = db
        self.temp_dir = os.path.join(CONFIG['TASK_DIR'], self.task_id)
        self.steps = [
            "获取页面内容",
            "生成对话内容",
            "翻译对话内容",
            "合成中文语音",
            "合成英文语音",
            "生成中文字幕",
            "生成英文字幕",
            "合并中文音频",
            "合并英文音频"
        ]
        self.total_steps = len(self.steps)

    def update_progress(self, step_index: int, step_progress: int = 0, message: str = None):
        current_step = self.steps[step_index]
        progress_message = f"[{step_index + 1}/{self.total_steps}] {current_step}"
        if message:
            progress_message += f": {message}"
        
        update_task_status(
            task_id=self.task_id,
            status='processing',
            progress=progress_message,
            current_step=current_step,
            total_steps=self.total_steps,
            step_progress=step_progress,
            db=self.db
        )

    def process_task(self):
        try:
            # 步骤1: 获取页面内容
            self.update_progress(0, 0, "正在获取页面...")
            text_content, title = self.fetch_url_content()
            self.update_progress(0, 100, f"获取完成，内容长度: {len(text_content)}字")

            # 步骤2: 生成对话内容
            self.update_progress(1, 0, "正在生成对话...")
            dialogue = self.generate_dialogue(text_content)
            self.save_dialogue(dialogue, "cn")
            self.update_progress(1, 100, f"生成完成，共{len(dialogue)}条对话")

            # 步骤3: 翻译对话内容
            self.update_progress(2, 0, "正在翻译对话...")
            en_dialogue = self.translate_dialogue(dialogue)
            self.save_dialogue(en_dialogue, "en")
            self.update_progress(2, 100, "翻译完成")

            # 步骤4-5: 合成语音
            cn_audio_files = self.synthesize_audio(dialogue, "cn", 3)
            en_audio_files = self.synthesize_audio(en_dialogue, "en", 4)

            # 步骤6-7: 生成字幕
            cn_subtitle_content = self.generate_subtitles(dialogue, en_dialogue, cn_audio_files, "cn", 5)
            en_subtitle_content = self.generate_subtitles(dialogue, en_dialogue, en_audio_files, "en", 6)

            # 保存字幕文件
            self.save_subtitles(cn_subtitle_content, "cn")
            self.save_subtitles(en_subtitle_content, "en")

            # 步骤8-9: 合并音频
            self.merge_audio(cn_audio_files, "cn", 7)
            self.merge_audio(en_audio_files, "en", 8)

            # 任务完成
            self.complete_task()

        except Exception as e:
            self.handle_error(str(e))

    def fetch_url_content(self):
        text_content, title = fetch_url_content(self.url, self.task_id)
        if not text_content or len(text_content) < 4:
            raise Exception("获取页面内容失败或内容太短")
        return text_content, title

    def generate_dialogue(self, text_content):
        dialogue = generate_dialogue(text_content)
        if not dialogue:
            raise Exception("对话生成失败")
        return dialogue

    def translate_dialogue(self, dialogue):
        translated_dialogue = translate_dialogue(dialogue)  # 假设这是一个新的翻译函数
        if not translated_dialogue:
            raise Exception("对话翻译失败")
        return translated_dialogue

    def synthesize_audio(self, dialogue, lang, step_index):
        audio_files = []
        total_dialogues = len(dialogue)
        for i, item in enumerate(dialogue):
            progress = int((i / total_dialogues) * 100)
            self.update_progress(step_index, progress, f"正在合成第 {i+1}/{total_dialogues} 条对话")
            
            anchor_type = CONFIG['ANCHOR_TYPE_MAP'].get(item['role']+f"_{lang}", CONFIG['ANCHOR_TYPE_MAP']['default'])
            
            if CONFIG['USE_OPENAI_TTS_MODEL']:
                # 使用 OpenAI TTS
                audio_content = tts_request(item['content'], anchor_type)
                if audio_content is None:
                    raise Exception(f"第 {i+1} 条{lang}对话音频生成失败")
                
                audio_file = os.path.join(self.temp_dir, f"{i:04d}_{lang}_{item['role']}.mp3")
                with open(audio_file, 'wb') as f:
                    f.write(audio_content)
            else:
                # 使用微软 TTS
                audio_file = generate_speech(item['content'], anchor_type)
                if not audio_file or not os.path.exists(audio_file):
                    raise Exception(f"第 {i+1} 条{lang}对话音频生成失败")
                
                # 将临时文件移动到任务目录
                final_audio_file = os.path.join(self.temp_dir, f"{i:04d}_{lang}_{item['role']}.mp3")
                shutil.move(audio_file, final_audio_file)
                audio_file = final_audio_file
                
            audio_files.append(audio_file)
        
        self.update_progress(step_index, 100, f"{lang}语音合成完成")
        return audio_files

    def generate_subtitles(self, cn_dialogue, en_dialogue, audio_files, lang, step_index):
        self.update_progress(step_index, 0, f"正在生成{lang}音频的双语字幕")
        subtitle_content = []
        current_time = 0
        for i, (cn_item, en_item, audio_file) in enumerate(zip(cn_dialogue, en_dialogue, audio_files)):
            audio_segment = AudioSegment.from_mp3(audio_file)
            duration = len(audio_segment) / 1000.0
            
            primary_content = cn_item['content']
            secondary_content = en_item['content']
            
            subtitle_content.append(self._create_subtitle_entry(i, current_time, duration, primary_content, secondary_content))
            
            current_time += duration
        
        self.update_progress(step_index, 100, f"{lang}音频的双语字幕生成完成")
        return subtitle_content

    def merge_audio(self, audio_files, lang, step_index):
        self.update_progress(step_index, 0, f"正在合并{lang}音频文件")
        output_file = os.path.join(self.temp_dir, f"{self.task_id}_{lang}.mp3")
        audio_segments = [AudioSegment.from_mp3(audio_file) for audio_file in audio_files]
        output_segment = sum(audio_segments)
        output_segment.export(output_file, format='mp3')
        
        # 清理临时音频文件
        for audio_file in audio_files:
            os.remove(audio_file)
        
        self.update_progress(step_index, 100, f"{lang}音频合并完成")

    def save_subtitles(self, subtitle_content, lang):
        subtitle_file = os.path.join(self.temp_dir, f"{self.task_id}_{lang}.srt")
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(subtitle_content))

    def complete_task(self):
        update_task_status(
            task_id=self.task_id,
            status='completed',
            progress="任务处理完成",
            current_step="完成",
            total_steps=self.total_steps,
            step_progress=100,
            db=self.db
        )
        self.task.audioUrlCn = f"/audio/{self.task_id}/{self.task_id}_cn.mp3"
        self.task.audioUrlEn = f"/audio/{self.task_id}/{self.task_id}_en.mp3"
        self.task.subtitleUrlCn = f"/subtitle/{self.task_id}/{self.task_id}_cn.srt"
        self.task.subtitleUrlEn = f"/subtitle/{self.task_id}/{self.task_id}_en.srt"
        self.db.commit()

    def handle_error(self, error_message):
        log(error_message)
        update_task_status(
            task_id=self.task_id,
            status='failed',
            progress=error_message,
            db=self.db
        )

    def _create_subtitle_entry(self, index: int, start_time: float, duration: float, primary_content: str, secondary_content: str) -> str:
        start = format_timestamp(start_time)
        end = format_timestamp(start_time + duration)
        return f"{index+1}\n{start} --> {end}\n{primary_content}\n{secondary_content}\n"

    def save_dialogue(self, dialogue, lang):
        dialogue_file = os.path.join(self.temp_dir, f"dialogue_{lang}.json")
        with open(dialogue_file, 'w', encoding='utf-8') as f:
            json.dump(dialogue, f, ensure_ascii=False, indent=2)
        log(f"已保存{lang}对话内容到文件: {dialogue_file}")

@error_handler
def execute_task(task: models.TaskModel):
    db = next(models.get_db())
    processor = TaskProcessor(task, db)
    
    try:
        processor.process_task()
    finally:
        db.close()

@error_handler
def tts_request(text, anchor_type):
    log(f"正在使用LangChain的OpenAI语音接口生成音频，文本: {text}, 角色: {anchor_type}")
    try:
        response = tts_client.audio.speech.create(
            model=CONFIG['TTS_MODEL'],
            voice=anchor_type,
            input=text
        )
        return response.content
    except Exception as e:
        log(f"音频生成失败: {str(e)}")
        return None

# 新增：时间戳格式化函数
def format_timestamp(seconds):
    """将秒数转换为 SRT 格式的时间戳 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def update_task_status(
    task_id: str, 
    status: str, 
    progress: str, 
    db: Session,
    current_step: str = None,
    total_steps: int = None,
    step_progress: int = None
):
    log(f"更新任务 {task_id} 状态: {status}, 进度: {progress}")
    
    task = db.query(models.TaskModel).filter(models.TaskModel.taskId == task_id).first()
    if task:
        task.status = status
        task.progress = progress
        task.updatedAt = datetime.now()
        if current_step is not None:
            task.current_step = current_step
        if total_steps is not None:
            task.total_steps = total_steps
        if step_progress is not None:
            task.step_progress = step_progress
        db.commit()
        log(f"任务 {task_id} 状态更新完成")

def get_prompt_template(template_name):
    template_file = os.path.join(os.path.dirname(__file__), 'prompt_templates.yaml')
    with open(template_file, 'r', encoding='utf-8') as f:
        templates = yaml.safe_load(f)
    
    if template_name not in templates:
        raise ValueError(f"Template '{template_name}' not found")
    
    return templates[template_name]

def create_chat_prompt(template_name):
    template = get_prompt_template(template_name)
    return ChatPromptTemplate.from_messages([
        ("system", template["system"]),
        ("human", template["human"]),
    ])

@error_handler
def generate_dialogue(text_content):
    log("开始生成对话内容")
    
    chat_prompt = create_chat_prompt("dialogue_generation")
    
    chain = chat_prompt | llm_chat | JsonOutputParser()
    
    all_content = []
    try:
        all_content = chain.invoke({"text_content": text_content})
        log(f"成功解析对话内容，共 {len(all_content)} 条对话")
    except Exception as e:
        log(f"解析对话内容时发生错误: {str(e)}")
    return all_content

def check_and_execute_incomplete_tasks():
    db = next(models.get_db())
    try:
        incomplete_tasks = (
            db.query(models.TaskModel)
            .filter(models.TaskModel.status.notin_(['completed', 'failed']))
            .all()
        )
        
        # 清理失败任务的文件夹
        failed_tasks = db.query(models.TaskModel).filter(models.TaskModel.status == 'failed').all()
        for task in failed_tasks:
            task_dir = os.path.join(CONFIG['TASK_DIR'], task.taskId)
            if os.path.exists(task_dir):
                log(f"清除已失败的任务文件夹: {task_dir}")
                shutil.rmtree(task_dir)
        
        if incomplete_tasks:
            log(f"发现 {len(incomplete_tasks)} 个未完成的任务")
            for task in incomplete_tasks:
                log(f"重新执行任务: {task.taskId}")
                threading.Thread(target=execute_task, args=(task,)).start()
        else:
            log("没有发现未完成的任务")
    except Exception as e:
        log(f"检查未完成任务时发生错误: {str(e)}")
    finally:
        db.close()

# 新增翻译函数
@error_handler
def translate_dialogue(dialogue):
    log("开始翻译对话内容")
    
    chat_prompt = create_chat_prompt("dialogue_translation")
    chain = chat_prompt | llm_chat | JsonOutputParser()
    
    translated_dialogue = []
    batch_size = 5  # 每批次翻译的对话数量
    
    for i in range(0, len(dialogue), batch_size):
        batch = dialogue[i:i+batch_size]
        log(f"正在翻译第 {i+1} 到 {min(i+batch_size, len(dialogue))} 条对话")
        
        try:
            batch_translated = chain.invoke({"content": batch})
            translated_dialogue.extend(batch_translated)
            log(f"成功翻译批次,共 {len(batch_translated)} 条对话")
        except Exception as e:
            log(f"翻译批次对话内容时发生错误: {str(e)}")
            # 如果批次翻译失败,尝试逐条翻译
            for item in batch:
                try:
                    single_translated = chain.invoke({"content": [item]})
                    translated_dialogue.extend(single_translated)
                    log(f"成功翻译单条对话")
                except Exception as e:
                    log(f"翻译单条对话内容时发生错误: {str(e)}")
                    # 如果单条翻译也失败,添加一个空的翻译结果以保持对话顺序
                    translated_dialogue.append({"role": item["role"], "content": ""})
    
    log(f"翻译完成,共 {len(translated_dialogue)} 条对话")
    return translated_dialogue

