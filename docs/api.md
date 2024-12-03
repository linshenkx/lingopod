# API 文档

## 认证说明

所有需要认证的API接口支持以下两种方式传递token:

1. 请求头方式 (推荐)
```
Authorization: Bearer <your_token>
```

2. URL查询参数方式
```
?token=<your_token>
```

例如:
```bash
# 使用请求头方式(推荐)
curl http://api.example.com/api/v1/auth/me \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 使用查询参数方式
curl http://api.example.com/api/v1/auth/me?token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

**注意:** 出于安全考虑，建议优先使用请求头方式传递token，因为URL查询参数可能会被记录在服务器日志中。

## 模型说明

### Task 任务模型

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| taskId | string | 是 | 任务唯一标识 |
| url | string | 是 | 待处理的URL |
| status | string | 是 | 任务整体状态：pending/processing/completed/failed |
| progress | string | 是 | 当前步骤的执行状态：waiting/processing/completed/failed |
| title | string | 否 | 文章标题 |
| current_step | string | 否 | 当前执行的步骤名称 |
| current_step_index | integer | 否 | 当前步骤序号(从0开始) |
| total_steps | integer | 否 | 总步骤数 |
| step_progress | integer | 否 | 当前步骤的进度(0-100) |
| audioUrlCn | string | 否 | 中文音频文件URL |
| audioUrlEn | string | 否 | 英文音频文件URL |
| subtitleUrlCn | string | 否 | 中文字幕文件URL |
| subtitleUrlEn | string | 否 | 英文字幕文件URL |
| user_id | integer | 是 | 所属用户ID |
| is_public | boolean | 是 | 是否公开 |
| created_by | integer | 是 | 创建者ID |
| updated_by | integer | 否 | 更新者ID |
| createdAt | integer | 是 | 创建时间(毫秒时间戳) |
| updatedAt | integer | 是 | 更新时间(毫秒时间戳) |
| progress_message | string | 否 | 进度消息，用于显示当前执行状态的详细信息 |

### TaskStatus 任务状态枚举

- `pending`: 待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

### TaskProgress 进度状态枚举

- `waiting`: 等待处理
- `processing`: 处理中
- `completed`: 已完成
- `failed`: 失败

### 状态流转说明

1. 任务创建时:
   - status = pending
   - progress = waiting
   - current_step_index = null
   - total_steps = null
   - step_progress = 0

2. 任务开始处理:
   - status = processing
   - progress = processing
   - current_step_index = 0
   - total_steps = N (总步骤数)
   - step_progress = 0

3. 步骤执行过程中:
   - status 保持为 processing
   - progress 根据当前步骤执行状态变化
   - current_step_index 表示当前执行的步骤序号(从0开始)
   - step_progress 具体步骤的进度百分比(0-100)
   - 总体进度计算方式: (current_step_index  + 1) / total_steps

4. 任务完成时:
   - status = completed
   - progress = completed
   - current_step_index = total_steps - 1
   - step_progress = 100

5. 任务失败时:
   - status = failed
   - progress = failed
   - step_progress = 0

## API 接口

## 认证相关接口

### 1. 用户登录

**路径:** `/api/v1/auth/login`  
**方法:** `POST`  
**权限:** 公开

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| username | string | form-data | 是 | 用户名,长度≥3 |
| password | string | form-data | 是 | 密码 |

**响应:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
}
```

**错误响应:**
- 401: 用户名或密码错误
- 400: 用户已被禁用

**说明:** 使用OAuth2密码模式进行认证，返回JWT token，有效期可配置

**示例:**
```bash
# 请求
curl -X POST http://api.example.com/api/v1/auth/login \
    -d "username=testuser" \
    -d "password=testpass"

# 成功响应
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer"
}

# 失败响应
{
    "detail": "用户名或密码错误"
}
```

### 2. 用户注册

**路径:** `/api/v1/auth/register`  
**方法:** `POST`  
**权限:** 公开

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| username | string | json | 是 | 用户名,长度≥3 |
| password | string | json | 是 | 密码 |
| nickname | string | json | 否 | 昵称,默认同用户名 |

**响应:**
```json
{
    "username": "newuser",
    "nickname": "New User"
}
```

**错误响应:**
- 403: 注册功能已关闭
- 400: 用户名已存在

**说明:** 注册功能可通过系统配置(ALLOW_REGISTRATION)关闭

**示例:**
```bash
# 请求
curl -X POST http://api.example.com/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{
        "username": "newuser",
        "password": "password123",
        "nickname": "New User"
    }'

# 成功响应
{
    "username": "newuser",
    "nickname": "New User"
}

# 失败响应
{
    "detail": "用户名已存在"
}
```

### 3. 获取当前用户信息

**路径:** `/api/v1/auth/me`  
**方法:** `GET`  
**权限:** 用户

**请求头:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | 是 | Bearer token |

**响应:**
```json
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000,
    "tts_voice": "zh-CN-XiaoxiaoNeural",
    "tts_rate": 1.0
}
```

**说明:** 需要在请求头携带有效的Bearer Token

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/auth/me \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000,
    "tts_voice": "zh-CN-XiaoxiaoNeural",
    "tts_rate": 1.0
}
```

## 用户管理接口

### 1. 获取用户列表

**路径:** `/api/v1/users`  
**方法:** `GET`  
**权限:** 管理员

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| limit | integer | query | 否 | 每页数量(1-100),默认10 |
| offset | integer | query | 否 | 偏移量，默认0 |
| username | string | query | 否 | 用户名(模糊查询) |
| is_active | boolean | query | 否 | 是否启用 |
| start_date | integer | query | 否 | 开始时间戳(毫秒) |
| end_date | integer | query | 否 | 结束时间戳(毫秒) |

**响应:**
```json
{
    "total": 100,
    "items": [
        {
            "id": 1,
            "username": "user1",
            "nickname": "User One",
            "is_active": true,
            "is_admin": false,
            "created_at": 1710925200000
        }
    ]
}
```

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/users?limit=10&offset=0&username=testuser&is_active=true&start_date=1710925200000&end_date=1710925200000 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
{
    "total": 100,
    "items": [
        {
            "id": 1,
            "username": "user1",
            "nickname": "User One",
            "is_active": true,
            "is_admin": false,
            "created_at": 1710925200000
        }
    ]
}
```

### 2. 获取用户信息

**路径:** `/api/v1/users/{user_id}`  
**方法:** `GET`  
**权限:** 管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | integer | 是 | 用户ID |

**响应:** UserResponse
```json
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000
}
```

**错误响应:**
- 404: 用户未找到

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/users/1 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000
}
```

### 3. 更新用户状态

**路径:** `/api/v1/users/{user_id}/status`  
**方法:** `PATCH`  
**权限:** 管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|----------|------|
| user_id | integer | 是 | 用户ID |

**请求体:**
```json
{
    "is_active": true
}
```

**响应:** UserResponse
```json
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000
}
```

**说明:** 用于启用或禁用用户账号

**错误响应:**
- 404: 用户未找到

**示例:**
```bash
# 请求
curl -X PATCH http://api.example.com/api/v1/users/1/status \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
    -H "Content-Type: application/json" \
    -d '{"is_active": true}'

# 响应
{
    "id": 1,
    "username": "testuser",
    "nickname": "Test User",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000
}
```

### 4. 删除用户

**路径:** `/api/v1/users/{user_id}`  
**方法:** `DELETE`  
**权限:** 管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_id | integer | 是 | 用户ID |

**响应:** 204 No Content

**说明:**
- 删除用户时会同时删除该用户的所有任务及相关文件
- 删除作不可恢复

**错误响应:**
- 404: 用户未找到

**示例:**
```bash
# 请求
curl -X DELETE http://api.example.com/api/v1/users/1 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
204 No Content
```

### 5. 更新当前用户信息

**路径:** `/api/v1/users/me`  
**方法:** `PATCH`  
**权限:** 用户

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| nickname | string | json | 否 | 昵称 |
| email | string | json | 否 | 邮箱地址 |
| tts_voice | string | json | 否 | TTS语音选项 |
| tts_rate | integer | json | 否 | TTS语速(-100到100) |

**响应:** UserResponse

**说明:** 用于更新当前用户的昵称、邮箱地址、TTS语音选项和TTS语速

**错误响应:**
- 400: 无效的请求参数

**示例:**
```bash
# 请求
curl -X PATCH http://api.example.com/api/v1/users/me \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
    -H "Content-Type: application/json" \
    -d '{
        "nickname": "New Nickname",
        "email": "newemail@example.com",
        "tts_voice": "zh-CN-YunxiNeural",
        "tts_rate": 0
    }'

# 响应
{
    "id": 1,
    "username": "testuser",
    "nickname": "New Nickname",
    "is_active": true,
    "is_admin": false,
    "created_at": 1710925200000,
    "tts_voice": "zh-CN-YunxiNeural",
    "tts_rate": 0
}
```

### 6. 修改当前用户密码

**路径:** `/api/v1/users/me/password`  
**方法:** `POST`  
**权限:** 用户

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| old_password | string | json | 是 | 旧密码 |
| new_password | string | json | 是 | 新密码 |

**响应:**
```json
{
    "message": "密码修改成功"
}
```

**错误响应:**
- 400: 旧密码错误

**说明:** 用户修改自己的登录密码,需要验证旧密码

**示例:**
```bash
# 请求
curl -X POST http://api.example.com/api/v1/users/me/password \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
    -H "Content-Type: application/json" \
    -d '{
        "old_password": "oldpass123",
        "new_password": "newpass123"
    }'

# 响应
{
    "message": "密码修改成功"
}
```

### 7. 健康检查

**路径:** `/api/v1/users/health`  
**方法:** `GET`  
**权限:** 公开

**响应:**
```json
{
    "status": "ok",
    "message": "服务正常运行"
}
```

**说明:** 
- 用于检查用户服务是否正常运行
- 不需要认证即可访问
- 适用于负载均衡器健康检查

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/users/health

# 响应
{
    "status": "ok",
    "message": "服务正常运行"
}
```

## 任务相关接口

### 1. 创建任务

**路径:** `/api/v1/tasks`  
**方法:** `POST`  
**权限:** 用户

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| url | string | json | 是 | 任务URL |
| is_public | boolean | json | 否 | 是否公开,默认false |

**响应:** TaskResponse (status_code: 201)
```json
{
    "taskId": "task-123",
    "url": "https://example.com/article",
    "status": "pending",
    "progress": "waiting",
    "title": null,
    "current_step": null,
    "total_steps": null,
    "step_progress": null,
    "audioUrlCn": null,
    "audioUrlEn": null,
    "subtitleUrlCn": null,
    "subtitleUrlEn": null,
    "is_public": false,
    "user_id": 1,
    "created_by": 1,
    "updated_by": null,
    "createdAt": 1710925200000,
    "updatedAt": 1710925200000,
    "progress_message": "等待处理"
}
```

**说明:** 创建后任务会自动开始处理

**示例:**
```bash
# 请求
curl -X POST http://api.example.com/api/v1/tasks \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
    -H "Content-Type: application/json" \
    -d '{
        "url": "https://example.com/article",
        "is_public": true
    }'

# 响应
{
    "taskId": "task-123",
    "url": "https://example.com/article",
    "status": "pending",
    "progress": "waiting",
    "title": null,
    "current_step": null,
    "total_steps": null,
    "step_progress": null,
    "audioUrlCn": null,
    "audioUrlEn": null,
    "subtitleUrlCn": null,
    "subtitleUrlEn": null,
    "is_public": true,
    "user_id": 1,
    "created_by": 1,
    "updated_by": null,
    "createdAt": 1710925200000,
    "updatedAt": 1710925200000,
    "progress_message": "等待处理"
}
```

### 2. 获取任务详情

**路径:** `/api/v1/tasks/{task_id}`  
**方法:** `GET`  
**权限:** 用户

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应:** TaskResponse
```json
{
    "taskId": "task-123",
    "url": "https://example.com/article",
    "status": "completed",
    "progress": "completed",
    "title": "示例文章",
    "current_step": "翻译对话内容",
    "total_steps": 5,
    "step_progress": 100,
    "audioUrlCn": "/audio/task-123/task-123_cn.mp3",
    "audioUrlEn": "/audio/task-123/task-123_en.mp3",
    "subtitleUrlCn": "/subtitle/task-123/task-123_cn.srt",
    "subtitleUrlEn": "/subtitle/task-123/task-123_en.srt",
    "is_public": true,
    "user_id": 1,
    "created_by": 1,
    "updated_by": 1,
    "createdAt": 1710925200000,
    "updatedAt": 1710925200000,
    "progress_message": "任务执行完成"
}
```

**说明:**
- 会自动检查并更新处理中任务的状态
- 用户只能访问自己的任务或公开任务

**错误响应:**
- 404: 任务未找到
- 403: 无权访问该任务

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/tasks/task-123 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
{
    "taskId": "task-123",
    "url": "https://example.com/article",
    "status": "completed",
    "progress": "任务完成",
    "title": "示例文章",
    "is_public": true,
    "audioUrlCn": "/audio/task-123/task-123_cn.mp3",
    "audioUrlEn": "/audio/task-123/task-123_en.mp3",
    "subtitleUrlCn": "/subtitle/task-123/task-123_cn.srt",
    "subtitleUrlEn": "/subtitle/task-123/task-123_en.srt",
    "created_at": 1710925200000,
    "updated_at": 1710925200000
}
```

### 3. 获取任务列表

**路径:** `/api/v1/tasks`  
**方法:** `GET`  
**权限:** 用户

**请求参数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| limit | integer | query | 否 | 每页数量(1-100),默认10 |
| offset | integer | query | 否 | 偏移量，默认0 |
| status | string | query | 否 | 任务状态(pending/processing/completed/failed) |
| start_date | integer | query | 否 | 开始时间戳(毫秒) |
| end_date | integer | query | 否 | 结束时间戳(毫秒) |
| is_public | boolean | query | 否 | 是否公开 |
| title_keyword | string | query | 否 | 标题关键词 |
| url_keyword | string | query | 否 | URL关键词 |

**响应:**
```json
{
    "total": 100,
    "items": [
        {
            "taskId": "task-123",
            "url": "https://example.com/article",
            "status": "completed",
            "progress": "已完成",
            "createdAt": 1710925200000,
            "updatedAt": 1710925200000,
            "title": "示例文章",
            "audioUrlCn": "/audio/task-123/task-123_cn.mp3",
            "audioUrlEn": "/audio/task-123/task-123_en.mp3",
            "subtitleUrlCn": "/subtitle/task-123/task-123_cn.srt",
            "subtitleUrlEn": "/subtitle/task-123/task-123_en.srt",
            "is_public": true
        }
    ]
}
```

**说明:** 
- 普通用户只能看到自己的任务和其他用户的公开任务
- 管理员可以看到所有任务
- 返回的任务列表按更新时间序排序

**示例:**
```bash
# 获取第一页10条任务
curl http://api.example.com/api/v1/tasks?limit=10&offset=0 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 获取已完成的任务
curl http://api.example.com/api/v1/tasks?status=completed \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 获取最近24小时的公开任务
curl http://api.example.com/api/v1/tasks?start_date=1710838800000&is_public=true \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 按标题搜索任务
curl http://api.example.com/api/v1/tasks?title_keyword=测试 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 按URL搜索任务
curl http://api.example.com/api/v1/tasks?url_keyword=example.com \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 组合查询
curl http://api.example.com/api/v1/tasks?title_keyword=测试&status=completed&limit=10 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

**错误响应:**
- 401: 未授权访问
- 400: 无效的查询参数

### 4. 删除任务

**路径:** `/api/v1/tasks/{task_id}`  
**方法:** `DELETE`  
**权限:** 用户/管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应:**
```json
{
    "message": "任务删除成功"
}
```

**说明:**
- 删除任务时会同时删除相关的任务文件
- 普通用户只能删除自己的任务
- 管理员可删除所有任务

**错误响应:**
- 404: 任务未找到
- 403: 无权删除该任务

**示例:**
```bash
# 请求
curl -X DELETE http://api.example.com/api/v1/tasks/task-123 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
{
    "message": "任务删除成功"
}
```

### 5. 获取任务文件

**路径:** `/api/v1/tasks/files/{task_id}/{filename}`  
**方法:** `GET`  
**权限:** 用户

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |
| filename | string | 是 | 文件名 |

**响应:** FileResponse

**说明:**
- 支持的文件类型:
  - .mp3: audio/mpeg
  - .srt: application/x-subrip
  - 其他: text/plain
- 用户只能访问自己的任务文件或公开任务文件

**错误响应:**
- 404: 任务或文件不存在
- 403: 无权访问该文件

**示例:**
```bash
# 请求
curl http://api.example.com/api/v1/tasks/files/task-123/task-123_cn.mp3 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 响应
二进制文件内容(audio/mpeg)
```

### 6. 重试失败任���

**路径:** `/api/v1/tasks/{task_id}/retry`  
**方法:** `POST`  
**权限:** 用户/管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

**响应:**
```json
{
    "message": "Task retry started"
}
```

**说明:**
- 只能重试状态为 failed 的任务
- 普通用户只能重试自己的任务
- 管理员可重试所有任务
- 重试会从上次失败的步骤继续执行

**错误响应:**
- 404: 任务未找到
- 403: 无权重试该任务
- 400: 只有失败的任务可以重试

**示例:**
```bash
# 请求
curl -X POST http://api.example.com/api/v1/tasks/task-123/retry \
-H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
响应
{
"message": "Task retry started"
}
失败应
{
    "detail": "Only failed tasks can be retried"
}
```

### 7. 更新任务信息

**路径:** `/api/v1/tasks/{task_id}`  
**方法:** `PATCH`  
**权限:** 用户/管理员

**路径参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| task_id | string | 是 | 任务ID |

**请求数:**

| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| title | string | json | 否 | 任务标题 |
| is_public | boolean | json | 否 | 是否公开 |

**响应:** TaskResponse

**说明:** 
- 用户只能更新自己的任务
- 管理员可以更新所有任务
- 只能更新任务标题和公开状态

**错误响应:**
- 404: 任务未找到
- 403: 无权更新该任务

**示例:**
```bash
# 请求
curl -X PATCH http://api.example.com/api/v1/tasks/task-123 \
    -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
    -H "Content-Type: application/json" \
    -d '{
        "title": "新标题",
        "is_public": true
    }'

# 响应
{
    "taskId": "task-123",
    "url": "https://example.com/article",
    "status": "completed",
    "progress": "任务完成",
    "title": "新标题",
    "is_public": true,
    "audioUrlCn": "/audio/task-123/task-123_cn.mp3",
    "audioUrlEn": "/audio/task-123/task-123_en.mp3",
    "subtitleUrlCn": "/subtitle/task-123/task-123_cn.srt",
    "subtitleUrlEn": "/subtitle/task-123/task-123_en.srt",
    "created_at": 1710925200000,
    "updated_at": 1710925200000
}
```

## 配置管理接口

### 1. 获取所有配置

**路径:** `/api/v1/configs`  
**方法:** `GET`  
**权限:** 管理员

**响应:**
```json
{
    "configs": {
        "API_KEY": {
            "key": "API_KEY",
            "value": "sk-xxx",
            "type": "str",
            "description": "API密钥"
        },
        "MODEL": {
            "key": "MODEL",
            "value": "Qwen/Qwen2.5-7B-Instruct",
            "type": "str",
            "description": "模型名称"
        }
    }
}
```

### 2. 更新配置

**路径:** `/api/v1/configs/{key}`  
**方法:** `PUT`  
**权限:** 管理员

**请求参数:**
| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| key | string | path | 是 | 配置键名 |
| value | any | json | 是 | 配置值 |
| type | string | json | 是 | 值类型(str/int/float/bool/dict) |
| description | string | json | 否 | 配置说明 |

**响应:**
```json
{
    "message": "配置 API_KEY 更新成功"
}
```

**错误响应:**
- 400: 无效的配置键或更新失败
- 403: 无权限访问

### 3. 重置配置

**路径:** `/api/v1/configs/{key}`  
**方法:** `DELETE`  
**权限:** 管理员

**请求参数:**
| 参数名 | 类型 | 传参方式 | 必填 | 说明 |
|--------|------|----------|------|------|
| key | string | path | 是 | 配置键名 |

**响应:**
```json
{
    "message": "配置 API_KEY 已重置为默认值"
}
```

**错误响应:**
- 404: 配置不存在
- 403: 无权限访问

## 系统配置项说明

| 配置键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| ALLOW_REGISTRATION | bool | true | 是否允许注册 |
| HTTPS_PROXY | str | null | HTTPS代理地址 |
| API_BASE_URL | str | "https://api.example.com/v1" | API基础URL |
| API_KEY | str | "sk-aaa" | API密钥 |
| MODEL | str | "Qwen/Qwen2.5-7B-Instruct" | 模型名称 |
| USE_OPENAI_TTS_MODEL | bool | false | 是否使用OpenAI TTS模型 |
| TTS_BASE_URL | str | "http://localhost:5050/v1" | TTS服务基础URL |
| TTS_API_KEY | str | "abc" | TTS服务API密钥 |
| TTS_MODEL | str | "tts-1" | TTS模型名称 |
| ANCHOR_TYPE_MAP | dict | {...} | 主播声音类型映射 |

**说明:**
1. 以上配置项可以通过管理员接口修改
2. 所有配置项都可以通过环境变量设置
3. 数据库中的配置优先级高于环境变量
4. 重置配置会删除数据库中的配置，恢复为默认值或环境变量值
5. 配置更改后立即生效，无需重启服务
