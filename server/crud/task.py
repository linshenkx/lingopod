from typing import List, Optional
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task import TaskCreate, TaskUpdate, TaskQueryParams
from models.enums import TaskStatus, TaskProgress
from utils.time_utils import TimeUtil
import uuid
from sqlalchemy import or_
from core.logging import log
from models.user import User

class TaskCRUD():
    def create(self, db: Session, *, obj_in: TaskCreate, user: User) -> Task:
        """创建任务"""
        db_obj = Task(
            taskId=str(uuid.uuid4()),
            url=obj_in.url,
            status=TaskStatus.PENDING.value,
            progress=TaskProgress.WAITING.value,  # 添加初始进度状态
            is_public=obj_in.is_public,
            created_by=user.id,
            user_id=user.id,
            created_at=TimeUtil.now_ms(),
            updated_at=TimeUtil.now_ms()
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, task_id: str) -> Optional[Task]:
        return db.query(Task).filter(Task.taskId == task_id).first()
    
    def get_completed_tasks(self, db: Session) -> List[Task]:
        return (
            db.query(Task)
            .filter(Task.status == 'completed')
            .order_by(Task.updated_at.desc())
            .all()
        )

    def update(
        self, 
        db: Session,
        *,
        db_obj: Task,
        obj_in: TaskUpdate
    ) -> Task:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db_obj.updated_at = TimeUtil.now_ms()
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, task_id: str) -> Task:
        obj = db.query(Task).filter(Task.taskId == task_id).first()
        db.delete(obj)
        db.commit()
        return obj

    def get_tasks(
        self,
        db: Session,
        *,
        current_user_id: int,
        is_admin: bool,
        params: TaskQueryParams
    ) -> tuple[List[Task], int]:
        """获取任务列表"""
        query = db.query(Task)
        
        # 权限过滤 - 非管理员只能看到自己的任务
        if not is_admin:
            query = query.filter(Task.user_id == current_user_id)
        
        # 状态过滤
        if params.status:
            query = query.filter(Task.status == params.status)
        
        # 日期过滤
        if params.start_date:
            query = query.filter(Task.created_at >= params.start_date)
        if params.end_date:
            query = query.filter(Task.created_at <= params.end_date)
            
        # 用户过滤
        if params.user_id:
            query = query.filter(Task.user_id == params.user_id)
        
        # 标题关键词搜索
        if params.title_keyword:
            query = query.filter(Task.title.ilike(f"%{params.title_keyword}%"))
        
        # URL关键词搜索
        if params.url_keyword:
            query = query.filter(Task.url.ilike(f"%{params.url_keyword}%"))
        
        # 排序
        query = query.order_by(Task.created_at.desc())
        
        # 计算总数
        total = query.count()
        
        # 分页
        if params.offset:
            query = query.offset(params.offset)
        if params.limit:
            query = query.limit(params.limit)
        
        return query.all(), total

task = TaskCRUD()