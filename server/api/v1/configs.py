from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from db.session import get_db
from core.config import config_manager
from models.user import User
from auth.dependencies import get_admin_user
from models.system_config import SystemConfig
from schemas.config import ConfigUpdate, ConfigListResponse

router = APIRouter()

@router.get("")
async def get_all_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> ConfigListResponse:
    """获取所有配置项"""
    configs = config_manager.get_all_configs(db)
    return ConfigListResponse(configs=configs)

@router.put("/{key}")
async def update_config(
    key: str,
    config_update: ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Dict[str, str]:
    """更新配置项"""
    if not hasattr(config_manager._settings, key) or key not in config_manager.MUTABLE_CONFIGS:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的配置键或该配置不允许修改: {key}"
        )
    
    try:
        config_manager.update_config(
            db=db,
            key=key,
            value=config_update.value,
            type_name=config_update.type,
            description=config_update.description
        )
        return {"message": f"配置 {key} 更新成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新配置失败: {str(e)}")

@router.delete("/{key}")
async def reset_config(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """重置配置项为默认值"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config:
        db.delete(config)
        db.commit()
        config_manager.reload_db_config(db)
        return {"message": f"配置 {key} 已重置为默认值"}
    raise HTTPException(status_code=404, detail=f"配置 {key} 不存在于数据库中")
