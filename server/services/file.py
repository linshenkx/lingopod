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
        """获取任务文件的完整路径
        
        Args:
            task_id: 任务ID
            filename: 文件名 (从task.files结构中获取的文件名)
        """
        task_dir = os.path.join(settings.TASK_DIR, task_id)
        file_path = os.path.join(task_dir, filename)
        log.debug(f"构建文件路径: {file_path}")
        return file_path
    
    @staticmethod
    def get_task_file_name(level: str, lang: str, file_type: str, task_id: str) -> str:
        """生成标准化的文件名
        
        Args:
            level: 难度等级 (elementary/intermediate/advanced)
            lang: 语言 (cn/en)
            file_type: 文件类型 (audio/subtitle)
            task_id: 任务ID
        """
        # 文件扩展名映射
        extensions = {
            "audio": "mp3",
            "subtitle": "srt"
        }
        ext = extensions.get(file_type, "txt")
        
        # 生成标准化文件名: {level}_{lang}_{type}_{task_id}.{ext}
        filename = f"{level}_{lang}_{file_type}_{task_id}.{ext}"
        return filename
    
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

    @staticmethod
    def update_task_files(task_id: str, level: str, lang: str, file_type: str) -> str:
        """更新任务文件结构并返回生成的文件名
        
        Args:
            task_id: 任务ID
            level: 难度等级 (elementary/intermediate/advanced)
            lang: 语言 (cn/en)
            file_type: 文件类型 (audio/subtitle)
            
        Returns:
            str: 生成的标准化文件名
        """
        # 生成标准化文件名
        filename = FileService.get_task_file_name(
            level=level,
            lang=lang,
            file_type=file_type,
            task_id=task_id
        )
        
        # 确保任务目录存在
        FileService.create_task_directory(task_id)
        
        return filename

    @staticmethod
    def write_file(task_id: str, level: str, lang: str, file_type: str, content: bytes | str) -> str:
        """写入文件内容并返回文件名
        
        Args:
            task_id: 任务ID
            level: 难度等级
            lang: 语言
            file_type: 文件类型
            content: 文件内容(二进制或文本)
            
        Returns:
            str: 生成的标准化文件名
        """
        # 生成标准化文件名
        filename = FileService.get_task_file_name(
            level=level,
            lang=lang,
            file_type=file_type,
            task_id=task_id
        )
        
        # 获取完整文件路径
        file_path = FileService.get_task_file_path(task_id, filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入文件
        mode = 'wb' if isinstance(content, bytes) else 'w'
        encoding = None if isinstance(content, bytes) else 'utf-8'
        
        try:
            with open(file_path, mode=mode, encoding=encoding) as f:
                f.write(content)
            log.info(f"文件写入成功: {file_path}")
        except Exception as e:
            log.error(f"文件写入失败: {file_path}, 错误: {str(e)}")
            raise
            
        return filename
