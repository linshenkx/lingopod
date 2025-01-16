import edge_tts
import asyncio
import tempfile
import subprocess
import os
from typing import Optional, List, Dict
from core.config import settings
from core.logging import log
from tenacity import retry, stop_after_attempt, wait_exponential

class EdgeTTSService:
    def __init__(self):
        self.voice_mapping = {
            'alloy': 'en-US-AvaNeural',
            'echo': 'en-US-AndrewNeural',
            'fable': 'en-GB-SoniaNeural',
            'onyx': 'en-US-EricNeural',
            'nova': 'en-US-SteffanNeural',
            'shimmer': 'en-US-EmmaNeural'
        }
        self.default_language = os.getenv('DEFAULT_LANGUAGE', 'en-US')

    def generate_speech(self, text: str, voice: str, response_format: str = "mp3", speed: float = 1.0) -> str:
        """生成语音文件"""
        return asyncio.run(self._generate_audio(text, voice, response_format, speed))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_audio(self, text: str, voice: str, response_format: str, speed: float) -> str:
        """生成音频文件，失败时最多重试3次"""
        try:
            edge_tts_voice = self.voice_mapping.get(voice, voice)
            proxy = settings.HTTPS_PROXY
            temp_output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            if proxy:
                communicator = edge_tts.Communicate(text, edge_tts_voice, connect_timeout=5, proxy=proxy)
            else:
                communicator = edge_tts.Communicate(text, edge_tts_voice, connect_timeout=5)
            await communicator.save(temp_output_file.name)

            if response_format == "mp3" and speed == 1.0:
                return temp_output_file.name

            if not self._is_ffmpeg_installed():
                log.error("FFmpeg not available. Returning unmodified mp3 file.")
                return temp_output_file.name

            return self._convert_audio(temp_output_file.name, response_format, speed)
            
        except Exception as e:
            log.error(f"Edge TTS 生成音频失败: {str(e)}")
            log.error(f"使用的参数: text='{text}', voice='{edge_tts_voice}', format='{response_format}', speed={speed}")
            raise

    def _is_ffmpeg_installed(self) -> bool:
        """检查 FFmpeg 是否已安装"""
        try:
            subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _convert_audio(self, input_file: str, response_format: str, speed: float) -> str:
        """转换音频格式和速度"""
        converted_output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{response_format}")
        speed_filter = f"atempo={speed}" if response_format != "pcm" else f"asetrate=44100*{speed},aresample=44100"
        
        ffmpeg_command = [
            "ffmpeg", "-i", input_file,
            "-filter:a", speed_filter,
            "-f", response_format, "-y",
            converted_output_file.name
        ]

        try:
            subprocess.run(ffmpeg_command, check=True)
            return converted_output_file.name
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error in audio conversion: {e}")

    def get_models(self) -> List[Dict[str, str]]:
        """获取可用的 TTS 模型列表"""
        return [
            {"id": "tts-1", "name": "Text-to-speech v1"},
            {"id": "tts-1-hd", "name": "Text-to-speech v1 HD"}
        ]

    async def _get_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        """获取可用的语音列表"""
        all_voices = await edge_tts.list_voices()
        language = language or self.default_language
        return [
            {"name": v['ShortName'], "gender": v['Gender'], "language": v['Locale']}
            for v in all_voices 
            if language == 'all' or language is None or v['Locale'] == language
        ]

    def get_voices(self, language: Optional[str] = None) -> List[Dict[str, str]]:
        """获取可用的语音列表（同步版本）"""
        return asyncio.run(self._get_voices(language))
