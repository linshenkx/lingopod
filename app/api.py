import uuid
import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header, Response, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import threading
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import contextlib
from sqlalchemy.orm import Session
from app import server
from app import models
import shutil
from app.config import CONFIG

app = FastAPI()

class TaskCreate(BaseModel):
    url: str

class Task(BaseModel):
    taskId: str
    url: str
    status: str
    progress: str
    createdAt: str
    updatedAt: str
    audioUrl: Optional[str] = None
    title: Optional[str] = None
    dialogue: Optional[List[dict]] = None
    status_details: Optional[dict] = None
    subtitleUrl: Optional[str] = None  # 新增字幕文件链接字段
    subtitleUrlCn: Optional[str] = None
    subtitleUrlEn: Optional[str] = None

def log(message):
    print(f"[{datetime.now().isoformat()}] [API] {message}")

def update_task_files(task, task_dir):
    cn_audio_file = os.path.join(task_dir, f"{task.taskId}_cn.mp3")
    en_audio_file = os.path.join(task_dir, f"{task.taskId}_en.mp3")
    cn_subtitle_file = os.path.join(task_dir, f"{task.taskId}_cn.srt")
    en_subtitle_file = os.path.join(task_dir, f"{task.taskId}_en.srt")
    
    if os.path.exists(cn_audio_file) and os.path.exists(en_audio_file):
        task.status = 'completed'
        task.audioUrlCn = f"/audio/{task.taskId}/{task.taskId}_cn.mp3"
        task.audioUrlEn = f"/audio/{task.taskId}/{task.taskId}_en.mp3"
    
    if os.path.exists(cn_subtitle_file):
        task.subtitleUrlCn = f"/subtitle/{task.taskId}/{task.taskId}_cn.srt"
    
    if os.path.exists(en_subtitle_file):
        task.subtitleUrlEn = f"/subtitle/{task.taskId}/{task.taskId}_en.srt"
    
    title_file = os.path.join(task_dir, "title.txt")
    task.title = read_file_content(title_file)
    
    dialogue_file = os.path.join(task_dir, "dialogue_cn.json")
    task.dialogue = read_json_file(dialogue_file)
    
    status_file = os.path.join(task_dir, "status.json")
    task.status_details = read_json_file(status_file)

def read_file_content(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def read_json_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@app.post("/api/post_task")
async def post_task(task: models.TaskCreate, db: Session = Depends(models.get_db)):
    log(f"收到新任务请求: {task.url}")
    task_id = str(uuid.uuid4())
    log(f"生成任务ID: {task_id}")
    
    task_dir = os.path.join(CONFIG['TASK_DIR'], task_id)
    os.makedirs(task_dir, exist_ok=True)
    log(f"创建任务文件夹: {task_dir}")
    
    db_task = models.TaskModel(
        taskId=task_id,
        url=task.url,
        status="pending",
        progress="等待处理",
        createdAt=datetime.now(),
        updatedAt=datetime.now()
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    threading.Thread(target=server.execute_task, args=(db_task,)).start()
    
    log(f"任务创建成功，返回任务ID: {task_id}")
    return {"taskId": task_id}

@app.get("/api/get_task")
async def get_task(taskId: str, db: Session = Depends(models.get_db)):    
    task = db.query(models.TaskModel).filter(models.TaskModel.taskId == taskId).first()
    if not task:
        log(f"未找到任务，任务ID: {taskId}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务是否已完成但状态未更新
    if task.status == 'processing':
        task_dir = os.path.join(CONFIG['TASK_DIR'], taskId)
        cn_audio_file = os.path.join(task_dir, f"{taskId}_cn.mp3")
        en_audio_file = os.path.join(task_dir, f"{taskId}_en.mp3")
        if os.path.exists(cn_audio_file) and os.path.exists(en_audio_file):
            task.status = 'completed'
            task.progress = "任务处理完成"
            task.audioUrlCn = f"/audio/{taskId}/{taskId}_cn.mp3"
            task.audioUrlEn = f"/audio/{taskId}/{taskId}_en.mp3"
            db.commit()
    
    response_data = {
        "taskId": task.taskId,
        "status": task.status,
        "progress": task.progress,
        "current_step": task.current_step,
        "total_steps": task.total_steps,
        "step_progress": task.step_progress,
        "audioUrlCn": task.audioUrlCn,
        "audioUrlEn": task.audioUrlEn,
        "title": task.title,
        "url": task.url,
        "createdAt": task.createdAt.isoformat(),
        "updatedAt": task.updatedAt.isoformat(),
        "subtitleUrlCn": task.subtitleUrlCn,
        "subtitleUrlEn": task.subtitleUrlEn,
    }
    
    return response_data

@app.get("/api/get_list")
async def get_list(db: Session = Depends(models.get_db)):
    log("收到获取已完成任务列表请求")
    
    completed_tasks = (
        db.query(models.TaskModel)
        .filter(models.TaskModel.status == 'completed')
        .order_by(models.TaskModel.updatedAt.desc())
        .all()
    )
    
    for task in completed_tasks:
        task_dir = os.path.join(CONFIG['TASK_DIR'], task.taskId)
        update_task_files(task, task_dir)
        db.commit()
    
    # 添加序列化逻辑
    response_data = [{
        "taskId": task.taskId,
        "url": task.url,
        "status": task.status,
        "progress": task.progress,
        "createdAt": task.createdAt.isoformat(),
        "updatedAt": task.updatedAt.isoformat(),
        "title": task.title,
        "audioUrlCn": f"/audio/{task.taskId}/{task.taskId}_cn.mp3" if task.status == 'completed' else None,
        "audioUrlEn": f"/audio/{task.taskId}/{task.taskId}_en.mp3" if task.status == 'completed' else None,
        "subtitleUrlCn": f"/subtitle/{task.taskId}/{task.taskId}_cn.srt" if task.status == 'completed' else None,
        "subtitleUrlEn": f"/subtitle/{task.taskId}/{task.taskId}_en.srt" if task.status == 'completed' else None,
    } for task in completed_tasks]
    
    log(f"返回已完成任务列表，共 {len(completed_tasks)} 个任务")
    return response_data

@app.get("/audio/{taskId}/{filename}")
async def get_audio(
    taskId: str, 
    filename: str, 
    range: Optional[str] = Header(None)
):
    log(f"收到获取音频文件请求，任务ID: {taskId}，文件名: {filename}")
    file_path = os.path.join(CONFIG['TASK_DIR'], taskId, filename)
    
    if not os.path.exists(file_path):
        log(f"音频文件不存在，路径: {file_path}")
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    file_size = os.path.getsize(file_path)
    
    # 处理 Range 请求
    start = 0
    end = file_size - 1
    
    if range is not None:
        try:
            range_header = range.replace("bytes=", "").split("-")
            start = int(range_header[0])
            if range_header[1]:
                end = min(int(range_header[1]), file_size - 1)
        except (ValueError, IndexError) as e:
            log(f"Range 头解析错误: {e}")
            start = 0
            end = file_size - 1
    
    content_length = end - start + 1
    
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Cache-Control": "public, max-age=31536000",
        "Content-Type": "audio/mpeg",
        "Content-Disposition": f'inline; filename="{filename}"'
    }
    
    status_code = 206 if range else 200
    
    async def iterfile():
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 1024)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        except ConnectionResetError:
            log(f"客户端断开连接，任务ID: {taskId}")
        except Exception as e:
            log(f"音频流发生错误，任务ID: {taskId}, 错误: {str(e)}")
        finally:
            # 使用 contextlib.suppress 忽略关闭文件时可能的错误
            with contextlib.suppress(Exception):
                if not f.closed:
                    f.close()

    return StreamingResponse(
        iterfile(),
        status_code=status_code,
        headers=headers,
        media_type="audio/mpeg"
    )

@app.get("/subtitle/{taskId}/{filename}")
async def get_subtitle(taskId: str, filename: str):
    log(f"收到获取字幕文件请求，任务ID: {taskId}，文件名: {filename}")
    file_path = os.path.join(CONFIG['TASK_DIR'], taskId, filename)
    
    if not os.path.exists(file_path):
        log(f"字幕文件不存在，路径: {file_path}")
        raise HTTPException(status_code=404, detail="Subtitle file not found")
    
    headers = {
        "Cache-Control": "public, max-age=31536000",  # 缓存一年
        "Content-Type": "text/srt; charset=utf-8",
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    
    return FileResponse(
        file_path,
        headers=headers,
        media_type="text/srt"
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # 记录更多请求信息
    log(f"HTTP异常: {exc.status_code} - {exc.detail}")
    log(f"请求方法: {request.method} 请求路径: {request.url.path}")
    
    # 尝试获取请求的JSON数据，如果有异常则返回 None
    try:
        request_body = await request.json()
        log(f"请求体: {request_body}")
    except Exception as e:
        log(f"无法获取请求的JSON数据: {e}")
    
    # 返回自定义的错误响应
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    log(f"请求验证错误: {exc}")
    return JSONResponse(
        status_code=422,
        content={"message": "请求数据无效"},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    log(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "服务器内部错误"},
    )

@app.delete("/api/delete_task/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(models.get_db)):
    log(f"收到删除任务请求，任务ID: {task_id}")
    
    # 从数据库中查找并删除任务
    task = db.query(models.TaskModel).filter(models.TaskModel.taskId == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 删除任务相关的文件夹
    task_dir = os.path.join(CONFIG['TASK_DIR'], task_id)
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
        log(f"已删除任务文件夹: {task_dir}")
    
    # 从数据库中删除任务记录
    db.delete(task)
    db.commit()
    
    log(f"任务删除成功: {task_id}")
    return {"message": "Task deleted successfully"}

# 添加统一的静态文件服务，需在最下方避免覆盖
app.mount("/", StaticFiles(directory=CONFIG['STATIC_DIR'], html=True), name="static")

