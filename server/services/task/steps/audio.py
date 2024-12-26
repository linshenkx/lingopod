import json
from typing import Dict, List
import os
import shutil
from pydub import AudioSegment
import time

from services.task.utils.context import ContextManager
from utils.decorators import error_handler
from .base import BaseStep
from services.edgetts import EdgeTTSService
from openai import OpenAI
from core.config import settings
from core.logging import log
from services.task.utils.progress_tracker import ProgressTracker

class AudioStep(BaseStep):
    def __init__(
        self,
        level: str,
        lang: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"生成{level}-{lang}音频",
            input_files=[f"{level}/dialogue_{lang}.json"],
            output_files=[f"{level}/audio_files_{lang}.json"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.level = level
        self.lang = lang
        self.edge_tts = EdgeTTSService()
        self.openai_tts = OpenAI(
            base_url=settings.TTS_BASE_URL,
            api_key=settings.TTS_API_KEY
        )
        
    def _verify_audio_file(self, file_path: str) -> bool:
        """验证音频文件是否有效"""
        try:
            if not os.path.exists(file_path):
                return False
                
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
                
            audio_segment = AudioSegment.from_mp3(file_path)
            if len(audio_segment) == 0:
                return False
                
            return True
        except Exception as e:
            log.error(f"音频文件验证失败: {str(e)}")
            return False
    
    def _generate_audio_with_retry(self, item: dict, file_path: str, anchor_type: str, max_retries: int = 3) -> bool:
        """生成音频文件，支持重试"""
        for attempt in range(max_retries):
            try:
                if settings.USE_OPENAI_TTS_MODEL:
                    audio_content = self._sync_openai_tts_request(item['content'], anchor_type)
                    if audio_content is None:
                        raise Exception("OpenAI TTS 返回空内容")
                    
                    with open(file_path, 'wb') as f:
                        f.write(audio_content)
                else:
                    temp_audio_file = self.edge_tts.generate_speech(item['content'], anchor_type)
                    if not temp_audio_file or not os.path.exists(temp_audio_file):
                        raise Exception("Edge TTS 生成失败")
                    
                    shutil.move(temp_audio_file, file_path)
                
                # 验证生成的音频文件
                if self._verify_audio_file(file_path):
                    return True
                    
                log.warning(f"音频文件验证失败，尝试重试 {attempt + 1}/{max_retries}")
                
                # 如果验证失败，删除无效文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                # 添加短暂延迟后重试
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    
            except Exception as e:
                log.error(f"音频生成失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue
                
        return False
    
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行音频生成步骤"""
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            raise ValueError(f"缺少{self.level}难度等级目录")
            
        dialogue_key = f"{self.level}/dialogue_{self.lang}.json"
        dialogue_filename = context_manager.get(dialogue_key)
        if not dialogue_filename:
            raise ValueError(f"缺少{self.lang}对话内容")
            
        # 从文件读取对话内容
        dialogue_path = os.path.join(level_dir, dialogue_filename)
        
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue = json.load(f)
        
        if not dialogue:
            raise ValueError("对话内容为空")
            
        step_index = int(context_manager.get('current_step_index', 0))
        audio_files = []
        total = len(dialogue)
        
        for i, item in enumerate(dialogue):
            progress = int((i / total) * 100)
            self.progress_tracker.update_progress(
                step_index=step_index,
                step_name=self.name,
                progress=progress,
                message=f"正在合成第 {i+1}/{total} 条对话"
            )
            
            anchor_type = settings.ANCHOR_TYPE_MAP.get(
                item['role']+f"_{self.lang}", 
                settings.ANCHOR_TYPE_MAP['default']
            )

            audio_filename = f"{i:04d}_{self.lang}_{item['role']}.mp3"
            file_path = os.path.join(level_dir, audio_filename)
            
            if not self._generate_audio_with_retry(item, file_path, anchor_type):
                raise Exception(f"第 {i+1} 条{self.lang}对话音频生成失败，已重试最大次数:{item['content']}")
            
            audio_files.append({
                "index": i,
                "role": item["role"],
                "filename": audio_filename
            })
        
        # 保存音频文件列表
        audio_files_filename = f"audio_files_{self.lang}.json"
        audio_files_path = os.path.join(level_dir, audio_files_filename)
        
        with open(audio_files_path, 'w', encoding='utf-8') as f:
            json.dump(audio_files, f, ensure_ascii=False, indent=2)
            
        return {
            f"{self.level}/audio_files_{self.lang}.json": audio_files_filename
        }

    @error_handler
    def _sync_openai_tts_request(self, text, anchor_type):
        """同步方式调用 OpenAI TTS"""
        log.info(f"正在使用OpenAI语音接口生成音频，文本: {text}, 角色: {anchor_type}")
        try:
            response = self.openai_tts.audio.speech.create(
                model=settings.TTS_MODEL,
                voice=anchor_type,
                input=text
            )
            return response.content
        except Exception as e:
            log.error(f"音频生成失败: {str(e)}")
            return None