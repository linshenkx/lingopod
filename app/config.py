import os

def get_env_var(var_name, default_value):
    return os.environ.get(var_name, default_value)

CONFIG = {
    'API_BASE_URL': get_env_var('API_BASE_URL', 'https://api.example.com/v1'),
    'API_KEY': get_env_var('API_KEY', 'sk-aaa'),
    'MODEL': get_env_var('MODEL', 'Qwen/Qwen2.5-7B-Instruct'),
    'TTS_BASE_URL': get_env_var('TTS_BASE_URL', 'http://localhost:5050/v1'),
    'TTS_API_KEY': get_env_var('TTS_API_KEY', 'abc'),
    'TTS_MODEL': get_env_var('TTS_MODEL', 'tts-1'),
    'ANCHOR_TYPE_MAP': {
        'host_cn': get_env_var('ANCHOR_TYPE_HOST_CN', 'zh-CN-XiaoxiaoNeural'),
        'guest_cn': get_env_var('ANCHOR_TYPE_GUEST_CN', 'zh-CN-YunxiaNeural'),
        'host_en': get_env_var('ANCHOR_TYPE_HOST_EN', 'en-US-JennyNeural'),
        'guest_en': get_env_var('ANCHOR_TYPE_GUEST_EN', 'en-US-ChristopherNeural'),
        'default': get_env_var('ANCHOR_TYPE_DEFAULT', 'zh-CN-XiaoxiaoNeural')
    },
    'TASK_DIR': get_env_var('TASK_DIR', './data/tasks'),
    'DB_PATH': get_env_var('DB_PATH', './data/tasks.db'),
    'PORT': int(get_env_var('PORT', '28811')),  
    'HOST': get_env_var('HOST', '0.0.0.0'),
    'STATIC_DIR': 'static',
    'USE_OPENAI_TTS_MODEL': get_env_var('USE_OPENAI_TTS_MODEL', 'false').lower() == 'true'
}
