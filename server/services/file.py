import os
import json
import shutil
from core.config import settings
from core.logging import log
from models.enums import TaskProgress, TaskStatus

class FileService:
    @staticmethod
    def create_task_directory(task_id: str) -> str:
        task_dir = os.path.join(settings.TASK_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        log.info(f"创建任务文件夹: {task_dir}")
        return task_dir
    
    @staticmethod
    def get_task_file_path(task_id: str, filename: str) -> str:
        """获取任务文件的完整路径"""
        task_dir = os.path.join(settings.TASK_DIR, task_id)
        return os.path.join(task_dir, filename)
    
    @staticmethod
    def read_file_content(file_path: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            log.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
            raise

    @staticmethod
    def read_json_file(file_path: str) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            log(f"JSON 解析失败: {file_path}, 错误: {str(e)}")
            raise
        except Exception as e:
            log(f"读取 JSON 文件失败: {file_path}, 错误: {str(e)}")
            raise

    @staticmethod
    def delete_task_directory(task_id: str):
        task_dir = os.path.join(settings.TASK_DIR, task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
            log.info(f"已删除任务文件夹: {task_dir}")
