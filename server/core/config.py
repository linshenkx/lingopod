from pydantic_settings import BaseSettings
from typing import Dict, Any
import os
from sqlalchemy.orm import Session
from models.system_config import SystemConfig
from schemas.config import ConfigResponse

class Settings(BaseSettings):
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    TASK_DIR: str = os.path.join(BASE_DIR, 'data', 'tasks')
    DB_PATH: str = os.path.join(BASE_DIR, 'data', 'tasks.db')
    
    PORT: int = 28811
    HOST: str = '0.0.0.0'
    JWT_SECRET_KEY: str = 'your-secret-key'
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # 管理员账号配置
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    
    # 是否允许注册
    ALLOW_REGISTRATION: bool = True
        
    # 代理配置
    HTTPS_PROXY: str | None = None
    
    # API配置
    API_BASE_URL: str = 'https://api.example.com/v1'
    API_KEY: str = 'sk-aaa'
    MODEL: str = 'Qwen/Qwen2.5-7B-Instruct'
    USE_OPENAI_TTS_MODEL: bool = False
    TTS_BASE_URL: str = 'http://localhost:5050/v1'
    TTS_API_KEY: str = 'abc'
    TTS_MODEL: str = 'tts-1'
    ANCHOR_TYPE_MAP: Dict[str, str] = {
        'host_cn': 'zh-CN-XiaoxiaoNeural',
        'guest_cn': 'zh-CN-YunxiaNeural',
        'host_en': 'en-US-JennyNeural',
        'guest_en': 'en-US-ChristopherNeural',
        'default': 'zh-CN-XiaoxiaoNeural'
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

class ConfigManager:
    _instance = None
    _settings = None
    _db_config = {}
    _db_configs = []
    
    # 允许通过接口读取和修改的配置项
    MUTABLE_CONFIGS = {
        'API_BASE_URL',
        'API_KEY',
        'MODEL',
        'USE_OPENAI_TTS_MODEL',
        'TTS_BASE_URL',
        'TTS_API_KEY',
        'TTS_MODEL',
        'ANCHOR_TYPE_MAP',
        'HTTPS_PROXY',
        'ALLOW_REGISTRATION'
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._settings is None:
            self._settings = Settings()

    def get_all_configs(self, db: Session = None) -> Dict[str, ConfigResponse]:
        """获取所有可修改的配置项"""
        configs = {}
        for key in self.MUTABLE_CONFIGS:
            if hasattr(self._settings, key):
                # 获取默认值
                value = getattr(self._settings, key)
                type_name = self._infer_type(value)
                description = None
                
                # 如果提供了数据库会话，则从数据库获取最新配置
                if db:
                    db_config = db.query(SystemConfig).filter(
                        SystemConfig.key == key
                    ).first()
                    if db_config:
                        value = self._convert_value(db_config.value, db_config.type)
                        type_name = db_config.type
                        description = db_config.description
                
                configs[key] = ConfigResponse(
                    key=key,
                    value=value,
                    type=type_name,
                    description=description
                )
        return configs

    def _infer_type(self, value: Any) -> str:
        """推断值的类型"""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, dict):
            return "dict"
        return "str"

    def get_db_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取数据库中的配置项"""
        return {
            key: {
                'value': value,
                'type': next(
                    (config.type for config in self._db_configs 
                     if config.key == key), 
                    None
                ),
                'description': next(
                    (config.description for config in self._db_configs 
                     if config.key == key),
                    None
                )
            }
            for key, value in self._db_config.items()
        }

    def reload_db_config(self, db: Session):
        """从数据库重新加载配置"""
        configs = db.query(SystemConfig).all()
        self._db_config = {}
        for config in configs:
            value = self._convert_value(config.value, config.type)
            self._db_config[config.key] = value

    def _convert_value(self, value: str, type_name: str) -> Any:
        """根据类型转换配置值"""
        if type_name == "bool":
            return value.lower() in ("true", "1", "yes")
        elif type_name == "int":
            return int(value)
        elif type_name == "float":
            return float(value)
        elif type_name == "dict":
            return eval(value)  # 注意：这里需要安全处理
        return value

    def __getattr__(self, name: str):
        # 优先级：数据库配置 > 环境变量/Settings配置
        if name in self._db_config:
            return self._db_config[name]
        return getattr(self._settings, name)

    def update_config(self, db: Session, key: str, value: Any, type_name: str, description: str = None):
        """更新配置到数据库"""
        if key not in self.MUTABLE_CONFIGS:
            raise ValueError(f"配置项 {key} 不允许修改")
            
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if config:
            config.value = str(value)
            config.type = type_name
            config.description = description
        else:
            config = SystemConfig(
                key=key,
                value=str(value),
                type=type_name,
                description=description
            )
            db.add(config)
        
        db.commit()
        self.reload_db_config(db)

# 创建全局实例
config_manager = ConfigManager()
# 创建别名以兼容现有代码
settings = config_manager

# 为了向后兼容，保留 get_settings 函数
def get_settings():
    return settings
