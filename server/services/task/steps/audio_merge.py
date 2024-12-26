from typing import Dict, List
import os
from pydub import AudioSegment
import json

from services.task.utils.context import ContextManager
from .base import BaseStep
from core.logging import log
from services.task.utils.progress_tracker import ProgressTracker
from services.file import FileService

class AudioMergeStep(BaseStep):
    def __init__(
        self,
        level: str,
        lang: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"合并{level}-{lang}音频",
            input_files=[f"{level}/audio_files_{lang}.json"],
            output_files=[f"{level}/audio_{lang}.mp3"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.level = level
        self.lang = lang
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行音频合并步骤"""
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            raise ValueError(f"缺少{self.level}难度等级目录")

        audio_files_key = f"{self.level}/audio_files_{self.lang}.json"
        audio_files_filename = context_manager.get(audio_files_key)
        if not audio_files_filename:
            raise ValueError(f"缺少{self.lang}音频文件")
            
        # 从文件读取音频文件列表
        audio_files_path = os.path.join(level_dir, audio_files_filename)
        
        with open(audio_files_path, 'r', encoding='utf-8') as f:
            audio_files = json.load(f)
            
        if not audio_files:
            raise ValueError("音频文件列表为空")
                
        merged_file = self._merge_audio(audio_files, context_manager)
        
        # 更新files结构中对应语言的音频URL
        self.progress_tracker.update_files(
            level=self.level,
            lang=self.lang,
            file_type='audio'
        )
        
        # 清理临时音频文件
        self._cleanup_files(audio_files, context_manager)
        # 清理context
        context_manager.delete(audio_files_key)
        
        return {
            f"{self.level}/audio_{self.lang}.mp3": merged_file
        }
        
    def _merge_audio(self, audio_files: List[Dict], context_manager: ContextManager) -> str:
        """合并音频文件"""
        log.info(f"开始合并{self.lang}音频文件")
        
        merged = AudioSegment.empty()
        silence = AudioSegment.silent(duration=500)  # 0.5秒静音
        
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            raise ValueError("缺少level_dir")
            
        # 合并音频
        for audio_file in audio_files:
            try:
                audio_path = os.path.join(level_dir, audio_file["filename"])
                if not os.path.exists(audio_path):
                    raise FileNotFoundError(f"音频文件不存在: {audio_file['filename']}")
                
                segment = AudioSegment.from_file(audio_path)
                merged += segment + silence
                
            except Exception as e:
                log.error(f"合并音频文件失败: {str(e)}")
                raise ValueError(f"音频文件 {audio_file['filename']} 处理失败: {str(e)}")
        
        # 导出合并后的音频到字节流
        audio_data = merged.export(format="mp3").read()
        
        # 使用 FileService 写入文件
        filename = FileService.write_file(
            task_id=self.context_manager.get("taskId"),
            level=self.level,
            lang=self.lang,
            file_type='audio',
            content=audio_data
        )
        
        log.info(f"音频合并完成: {filename}")
        return filename
        
    def _cleanup_files(self, audio_files: List[Dict], context_manager: ContextManager) -> None:
        """清理临时音频文件和JSON配置文件"""
        level_dir = context_manager.get("level_dir")
        if not level_dir:
            log.warning("缺少level_dir，跳过清理")
            return
        
        # 清理音频文件
        for audio_file in audio_files:
            try:
                file_path = os.path.join(level_dir, audio_file["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                    log.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                log.error(f"删除临时文件失败: {str(e)}")
        
        # 清理JSON配置文件
        try:
            json_file = f"audio_files_{self.lang}.json"
            json_path = os.path.join(level_dir, json_file)
            if os.path.exists(json_path):
                os.remove(json_path)
                log.info(f"已删除配置文件: {json_path}")
        except Exception as e:
            log.error(f"删除配置文件失败: {str(e)}")
