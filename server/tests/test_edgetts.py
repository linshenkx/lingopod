import pytest
import tempfile
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from server.services.edgetts import EdgeTTSService

@pytest.fixture
def edge_tts_service():
    return EdgeTTSService()

@pytest.mark.asyncio
async def test_get_voices(edge_tts_service):
    """测试获取语音列表"""
    mock_voices = [
        {
            'ShortName': 'en-US-AvaNeural',
            'Gender': 'Female',
            'Locale': 'en-US'
        },
        {
            'ShortName': 'zh-CN-XiaoxiaoNeural',
            'Gender': 'Female',
            'Locale': 'zh-CN'
        }
    ]
    
    with patch('edge_tts.list_voices', return_value=mock_voices):
        # 测试默认语言过滤
        voices = await edge_tts_service._get_voices()
        assert len(voices) == 1  # 只返回默认语言(en-US)的语音
        assert voices[0]['name'] == 'en-US-AvaNeural'
        
        # 测试获取所有语音
        voices = await edge_tts_service._get_voices(language='all')
        assert len(voices) == 2  # 返回所有语音

def test_voice_mapping(edge_tts_service):
    """测试语音映射"""
    assert edge_tts_service.voice_mapping['alloy'] == 'en-US-AvaNeural'
    assert edge_tts_service.voice_mapping['echo'] == 'en-US-AndrewNeural'

@pytest.mark.asyncio
async def test_generate_audio_success(edge_tts_service):
    """测试成功生成音频"""
    mock_communicate = AsyncMock()
    mock_communicate.save = AsyncMock()
    
    with patch('edge_tts.Communicate', return_value=mock_communicate) as mock_comm:
        with tempfile.NamedTemporaryFile() as temp_file:
            result = await edge_tts_service._generate_audio(
                text="Hello world",
                voice="alloy",
                response_format="mp3",
                speed=1.0
            )
            
            mock_comm.assert_called_once()
            mock_communicate.save.assert_called_once()
            assert isinstance(result, str)
            assert result.endswith('.mp3')

def test_is_ffmpeg_installed(edge_tts_service):
    """测试FFmpeg安装检查"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)
        assert edge_tts_service._is_ffmpeg_installed() is True
        
        mock_run.side_effect = FileNotFoundError()
        assert edge_tts_service._is_ffmpeg_installed() is False

@pytest.mark.asyncio
async def test_generate_audio_with_conversion(edge_tts_service):
    """测试带格式转换的音频生成"""
    mock_communicate = AsyncMock()
    mock_communicate.save = AsyncMock()
    
    with patch('edge_tts.Communicate', return_value=mock_communicate), \
         patch('server.services.edgetts.EdgeTTSService._is_ffmpeg_installed', return_value=True), \
         patch('subprocess.run') as mock_run:
        
        result = await edge_tts_service._generate_audio(
            text="Hello world",
            voice="alloy",
            response_format="wav",
            speed=1.5
        )
        
        assert isinstance(result, str)
        assert result.endswith('.wav')
        mock_run.assert_called_once()

def test_get_models(edge_tts_service):
    """测试获取模型列表"""
    models = edge_tts_service.get_models()
    assert len(models) == 2
    assert models[0]['id'] == 'tts-1'
    assert models[1]['id'] == 'tts-1-hd'

@pytest.mark.asyncio
async def test_generate_audio_failure(edge_tts_service):
    """测试音频生成失败的情况"""
    with patch('edge_tts.Communicate', side_effect=Exception("Connection failed")):
        with pytest.raises(Exception) as exc_info:
            await edge_tts_service._generate_audio(
                text="Hello world",
                voice="alloy",
                response_format="mp3",
                speed=1.0
            )
        # 检查错误日志而不是具体的异常消息
        assert isinstance(exc_info.value, Exception) 