from typing import Dict, Any, Optional, List
from models.task import Task
import os
import json
from core.logging import log

class ContextManager:
    def __init__(self, task: Task, temp_dir: str):
        self.task = task
        self.temp_dir = temp_dir
        self.context_file = os.path.join(temp_dir, "context.json")
        self._context: Dict = {}
        
        # 确保目录存在
        os.makedirs(temp_dir, exist_ok=True)
        
        # 初始化基本上下文
        self._init_context()
        
    def _init_context(self):
        """初始化基本上下文"""
        if os.path.exists(self.context_file):
            self._context = self.load()
        else:
            self._context = {}
            
        # 从Task对象中获取基础信息
        task_dict = self.task.__dict__.copy()
        # 移除SQLAlchemy内部属性
        task_dict.pop('_sa_instance_state', None)
        
        # 添加temp_dir
        task_dict['temp_dir'] = self.temp_dir
        
        self._context.update(task_dict)
        self.save()
        
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文中的值"""
        return self._context.get(key, default)
        
    def set(self, key: str, value: Any):
        """设置上下文中的值"""
        self._context[key] = value
        self.save()
        
    def update(self, data: Dict):
        """批量更新上下文"""
        self._context.update(data)
        self.save()
        
    def delete(self, key: str):
        """删除上下文中的值"""
        if key in self._context:
            del self._context[key]
        self.save()
            
    def has_key(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._context
        
    def get_all(self) -> Dict:
        """获取完整上下文"""
        return self._context.copy()
        
    def validate_keys(self, required_keys: List[str]) -> List[str]:
        """验证必需的键是否存在，返回缺失的键列表"""
        return [key for key in required_keys if key not in self._context]
        
    def load(self) -> Dict:
        """从文件加载上下文"""
        if os.path.exists(self.context_file):
            with open(self.context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
        
    def save(self):
        """保存上下文到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(self.context_file), exist_ok=True)
        
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(self._context, f, ensure_ascii=False, indent=2)
        log.info(f"已保存上下文到: {self.context_file}")
