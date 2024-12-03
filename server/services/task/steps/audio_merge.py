from typing import Dict, List
import os
from pydub import AudioSegment
import json

from services.task.utils.context import ContextManager
from .base import BaseStep
from core.logging import log
from services.task.utils.progress_tracker import ProgressTracker

class AudioMergeStep(BaseStep):
    def __init__(
        self,
        lang: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"合并{lang}音频",
            input_files=[f"audio_files_{lang}.json"],
            output_files=[f"merged_audio_{lang}.mp3"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.lang = lang
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行音频合并步骤"""
        audio_files_key = f"audio_files_{self.lang}.json"
        audio_files_filename = context_manager.get(audio_files_key)
        if not audio_files_filename:
            raise ValueError(f"缺少{self.lang}音频文件")
            
        # 从文件读取音频文件列表
        temp_dir = context_manager.get("temp_dir")
        audio_files_path = os.path.join(temp_dir, audio_files_filename)
        
        with open(audio_files_path, 'r', encoding='utf-8') as f:
            audio_files = json.load(f)
            
        if not audio_files:
            raise ValueError("音频文件列表为空")
                
        merged_file = self._merge_audio(audio_files, context_manager)
        
        # 更新对应语言的音频URL
        task_id = context_manager.get("taskId")
        self.progress_tracker.db.refresh(self.progress_tracker.task)
        if self.lang == 'cn':
            self.progress_tracker.task.audioUrlCn = f"{merged_file}"
        else:
            self.progress_tracker.task.audioUrlEn = f"{merged_file}"
        
        self.progress_tracker.db.commit()
        
        # 清理临时音频文件
        self._cleanup_files(audio_files, context_manager)
        # 清理context
        context_manager.delete(audio_files_key)
        
        return {
            f"merged_audio_{self.lang}.mp3": merged_file
        }
        
    def _merge_audio(self, audio_files: List[Dict], context_manager: ContextManager) -> str:
        """合并音频文件"""
        log.info(f"开始合并{self.lang}音频文件")
        
        merged = AudioSegment.empty()
        silence = AudioSegment.silent(duration=500)  # 0.5秒静音
        
        task_id = context_manager.get("taskId")
        if not task_id:
            raise ValueError("缺少任务ID")
            
        temp_dir = context_manager.get("temp_dir")
        
        for audio_file in audio_files:
            try:
                audio_path = os.path.join(temp_dir, audio_file["filename"])
                segment = AudioSegment.from_file(audio_path)
                merged += segment + silence
                
            except Exception as e:
                log.error(f"合并音频文件失败: {str(e)}")
                continue
                
        output_file = f"{task_id}_{self.lang}.mp3"
        output_path = os.path.join(temp_dir, output_file)
        merged.export(output_path, format="mp3")
        
        log.info(f"音频合并完成: {output_file}")
        return output_file
        
    def _cleanup_files(self, audio_files: List[Dict], context_manager: ContextManager) -> None:
        """清理临时音频文件和JSON配置文件"""
        temp_dir = context_manager.get("temp_dir")
        
        # 清理音频文件
        for audio_file in audio_files:
            try:
                file_path = os.path.join(temp_dir, audio_file["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                    log.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                log.error(f"删除临时文件失败: {str(e)}")
        
        # 清理JSON配置文件
        try:
            json_file = f"audio_files_{self.lang}.json"
            json_path = os.path.join(temp_dir, json_file)
            if os.path.exists(json_path):
                os.remove(json_path)
                log.info(f"已删除配置文件: {json_path}")
        except Exception as e:
            log.error(f"删除配置文件失败: {str(e)}")
