import json
from typing import Dict, List
from .base import BaseStep
from services.task.utils.context import ContextManager
import os
from services.task.utils.progress_tracker import ProgressTracker
from pydub import AudioSegment

class SubtitleStep(BaseStep):
    def __init__(
        self,
        lang: str,
        progress_tracker: ProgressTracker,
        context_manager: ContextManager
    ):
        super().__init__(
            name=f"生成{lang}字幕",
            input_files=[
                "dialogue_cn.json",
                "dialogue_en.json",
                f"audio_files_{lang}.json"
            ],
            output_files=[f"subtitle_{lang}.srt"],
            progress_tracker=progress_tracker,
            context_manager=context_manager
        )
        self.lang = lang
        
    def _execute(self, context_manager: ContextManager) -> Dict:
        """执行字幕生成步骤"""
        dialogue_cn_filename = context_manager.get("dialogue_cn.json")
        dialogue_en_filename = context_manager.get("dialogue_en.json")
        audio_files_filename = context_manager.get(f"audio_files_{self.lang}.json")
        
        if not all([dialogue_cn_filename, dialogue_en_filename, audio_files_filename]):
            raise ValueError(f"缺少生成{self.lang}字幕所需的文件")
            
        # 从文件读取内容
        temp_dir = context_manager.get("temp_dir")
        
        # 读取中文对话
        dialogue_cn_path = os.path.join(temp_dir, dialogue_cn_filename)
        with open(dialogue_cn_path, 'r', encoding='utf-8') as f:
            dialogue_cn = json.load(f)
            
        # 读取英文对话    
        dialogue_en_path = os.path.join(temp_dir, dialogue_en_filename)
        with open(dialogue_en_path, 'r', encoding='utf-8') as f:
            dialogue_en = json.load(f)
            
        # 读取音频文件列表
        audio_files_path = os.path.join(temp_dir, audio_files_filename)
        with open(audio_files_path, 'r', encoding='utf-8') as f:
            audio_files = json.load(f)
        
        if not all([dialogue_cn, dialogue_en, audio_files]):
            raise ValueError("读取文件内容为空")
                
        subtitle_content = self._generate_subtitles(
            dialogue_cn,
            dialogue_en,
            audio_files
        )
        
        # 保存字幕文件
        task_id = context_manager.get("taskId")
        subtitle_filename = f"{task_id}_{self.lang}.srt"
        subtitle_path = os.path.join(temp_dir, subtitle_filename)
        
        # 更新对应语言的字幕URL
        self.progress_tracker.db.refresh(self.progress_tracker.task)
        if self.lang == 'cn':
            self.progress_tracker.task.subtitleUrlCn = f"{subtitle_filename}"
        else:
            self.progress_tracker.task.subtitleUrlEn = f"{subtitle_filename}"
        
        self.progress_tracker.db.commit()
        
        # 将字幕内容写入文件
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(subtitle_content))
        
        return {
            f"subtitle_{self.lang}.srt": subtitle_filename
        }
        
    def _generate_subtitles(
        self,
        dialogue_cn: List[Dict],
        dialogue_en: List[Dict],
        audio_files: List[Dict]
    ) -> List[str]:
        """生成双语字幕内容"""
        # 打印长度信息以便调试
        print(f"对话长度检查 - 中文: {len(dialogue_cn)}, 英文: {len(dialogue_en)}, 音频: {len(audio_files)}")
        
        subtitles = []
        current_time = 0
        silence_duration = 0.5
        
        for i, audio in enumerate(audio_files):
            try:
                # 安全地获取对话内容
                primary_content = dialogue_cn[i]["content"] if i < len(dialogue_cn) else "【缺失中文内容】"
                secondary_content = dialogue_en[i]["content"] if i < len(dialogue_en) else "【Missing English content】"
                
                # 从临时文件夹读取音频文件
                audio_path = os.path.join(self.context_manager.get("temp_dir"), audio["filename"])
                if not os.path.exists(audio_path):
                    raise ValueError(f"音频文件不存在: {audio_path}")
                
                # 添加文件大小检查
                file_size = os.path.getsize(audio_path)
                if file_size == 0:
                    raise ValueError(f"音频文件大小为0: {audio_path}")
                
                try:
                    # 直接使用 pydub 尝试加载文件
                    audio_segment = AudioSegment.from_mp3(audio_path)
                    if len(audio_segment) == 0:
                        raise ValueError(f"音频文件长度为0: {audio_path}")
                except Exception as e:
                    raise ValueError(f"音频文件读取失败: {audio_path}, 错误: {str(e)}")
                
                # 计算音频时长
                duration = len(audio_segment) / 1000.0  # 转换为秒
                audio_end_time = current_time + duration
                
                # 字幕结束时间延续到下一段开始
                subtitle_end_time = audio_end_time + silence_duration
                
                subtitle = self._format_subtitle(
                    i,
                    current_time,
                    subtitle_end_time,
                    primary_content,
                    secondary_content
                )
                subtitles.append(subtitle)
                
                current_time = audio_end_time + silence_duration
                
            except Exception as e:
                print(f"处理第 {i+1} 条字幕时出错: {str(e)}")
                print(f"当前索引: {i}")
                print(f"中文对话长度: {len(dialogue_cn)}")
                print(f"英文对话长度: {len(dialogue_en)}")
                print(f"音频文件长度: {len(audio_files)}")
                raise
        
        return subtitles
        
    def _format_subtitle(
        self,
        index: int,
        start: float,
        end: float,
        primary_content: str,
        secondary_content: str
    ) -> str:
        """格式化字幕
        Args:
            index: 字幕序号
            start: 开始时间（秒）
            end: 结束时间（秒）
            primary_content: 主要语言内容（中文）
            secondary_content: 次要语言内容（英文）
        Returns:
            格式化后的字幕文本
        """
        return (
            f"{index + 1}\n"
            f"{self._format_timestamp(start)} --> {self._format_timestamp(end)}\n"
            f"{primary_content}\n{secondary_content}\n"
        )
        
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        msecs = int((secs - int(secs)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{msecs:03d}"
