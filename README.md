# LingoPod (译播客) 🎙️

> 智能双语播客生成工具 - 将网页内容转化为沉浸式英语学习体验

## 🌟 项目简介

驱动工具，专注于将网页内容智能转换为双语播客。它不仅能自动生成引人入胜的中英文音频内容，还提供精准的双语字幕，为内容创作者和语言学习者提供了一站式的学习解决方案。

本项目包含:
- 服务端核心功能和简易Web界面
- [跨平台客户端应用](https://github.com/linshenkx/lingopod-client) (可选，支持Android/Web/Windows)


<div align="center">
  <img src="https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/home-dark.png" width="45%" alt="主页深色模式"/>
  <img src="https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/player-dark.png" width="45%" alt="播放器深色模式"/>
</div>


## ✨ 核心特性

- 🤖 智能网页内容提取与总结
- 💬 AI 驱动的自然对话生成
- 🗣️ 高品质中英文文本转语音 (TTS)
- 📝 自动生成双语字幕
- 🔄 支持中英文音频切换
- 🎵 智能音频合成与处理
- 🚀 RESTful API 支持
- 🎯 内置简易Web界面
- 📱 支持跨平台客户端应用

## 🛠️ 技术栈

### 服务端
- **后端**: Python 3.11, FastAPI, SQLAlchemy
- **内置前端**: HTML5, JavaScript
- **AI**: LangChain, OpenAI API
- **数据库**: SQLite
- **部署**: Docker

### 客户端 (可选)
- **框架**: Flutter 3.5.4+
- **平台**: Android/Web/Windows

## 🚀 安装与部署

项目依赖两个核心服务:
- **LLM 服务**: 通过 OpenAI 兼容接口对接,支持各类大语言模型，使用免费的qwen2.5-7b模型也可以达到较好效果
- **TTS 服务**: 支持两种模式：
  1. 微软 TTS（edge-tts）：默认模式，免费使用。非大陆地区需设置 HTTPS_PROXY 环境变量
  2. OpenAI TTS：通过设置 USE_OPENAI_TTS_MODEL=true 启用，需配置相应的 API

### 1. TTS 服务配置

#### 微软 TTS (默认模式)
- 默认使用 edge-tts，无需额外配置
- 非大陆地区用户需设置代理：
```bash
export HTTPS_PROXY="http://your-proxy:port"
```

#### OpenAI TTS (可选)
需要在启动时配置以下环境变量：
```bash
USE_OPENAI_TTS_MODEL=true
TTS_BASE_URL=your_tts_base_url
TTS_API_KEY=your_tts_api_key
TTS_MODEL=your_tts_model
```
可以参考[edge-tts-openai-cf-worker](https://github.com/linshenkx/edge-tts-openai-cf-worker)部署基于cloudflare workers的OpenAI TTS服务

### 2. 核心服务部署

1. 创建数据目录：
```bash
mkdir -p /path/to/lingopod/data
```

2. 启动容器：

#### 微软 TTS 模式（默认）
```bash
docker run -d \
  --name lingopod \
  --restart always \
  -p 28811:28811 \
  -v /path/to/lingopod/data:/opt/lingopod/data \
  -e PORT=28811 \
  -e API_BASE_URL=your_api_base_url \
  -e API_KEY=your_api_key \
  -e MODEL=your_model \
  -e HTTPS_PROXY="http://your-proxy:port" \
  linshen/lingopod:2.0
```

#### OpenAI TTS 模式
```bash
docker run -d \
  --name lingopod \
  --restart always \
  -p 28811:28811 \
  -v /path/to/lingopod/data:/opt/lingopod/data \
  -e PORT=28811 \
  -e API_BASE_URL=https://openai.example.com/v1 \
  -e API_KEY=abc \
  -e MODEL=Qwen/Qwen2.5-7B-Instruct \
  -e USE_OPENAI_TTS_MODEL=true \
  -e TTS_BASE_URL=https://tts.example.com/v1 \
  -e TTS_API_KEY=abc \
  -e TTS_MODEL=tts-1 \
  linshen/lingopod:2.0
```

访问服务：
- API接口：http://localhost:28811/api
- 管理后台：http://localhost:28811

容器管理：
```bash
# 查看容器日志
docker logs -f lingopod

# 停止并删除容器
docker stop lingopod && docker rm lingopod
```


### 3. 功能特点

#### 核心功能
- 智能网页内容提取与总结
  - 智能正文识别和广告过滤
  - AI驱动的内容优化和结构化处理
  - 关键信息提取与语义理解
- AI驱动的自然对话生成
  - 主持人与嘉宾角色设定
  - 自然流畅的对话风格
  - 专业术语智能处理
- 高品质中英文文本转语音(TTS)
  - 支持Edge-TTS和OpenAI TTS
  - 多种音色和语速选择
  - 智能音频合成与处理
- 自动生成双语字幕
  - 中英文字幕同步显示
  - 精准的时间轴对齐
  - 支持字幕样式配置

#### 用户系统
- 用户注册与认证
- 个人偏好设置
  - TTS音色选择
  - 语速调节
  - 音量设置
- 任务管理
  - 创建和监控任务
  - 支持公开/私有任务
  - 任务进度追踪
  - 文件下载管理

### 4. 开发指南

#### 本地开发环境配置

1. Conda环境配置:
```bash
# 创建conda环境
conda create -n lingopod python=3.11
conda activate lingopod

# 克隆项目
git clone https://github.com/linshenkx/lingopod.git
cd lingopod
```

2. 安装Poetry和项目依赖:
```bash
# 安装poetry
pip install poetry

# 配置poetry使用当前conda环境（可选）
poetry config virtualenvs.create false

# 安装项目依赖
poetry install
```

3. 启动开发服务器:
```bash
poetry run python server/main.py
```

### 5. API文档

访问 `http://localhost:28811/docs` 查看完整的API文档。

认证支持以下两种方式：
1. 请求头方式 (推荐)
```
Authorization: Bearer <your_token>
```

2. URL查询参数方式
```
?token=<your_token>
```

### 6. 管理后台

访问 `http://localhost:28811` 进入管理后台，支持：
- 用户管理
- 任务管理
- 系统设置
- 个人信息配置


## ⚙️ 配置说明

配置可通过config.py或环境变量设置，所有配置项均支持环境变量注入。

### 必选配置

```bash
# LLM 服务配置（必选）
API_BASE_URL="https://api.example.com/v1"  # LLM API 基础地址
API_KEY="your_api_key"                     # API 密钥
MODEL="Qwen/Qwen2.5-7B-Instruct"          # 使用的模型
```

### TTS 配置

```bash
# TTS 模式选择
USE_OPENAI_TTS_MODEL=false                 # 是否使用 OpenAI TTS（默认为 false，使用微软 TTS）

# OpenAI TTS 配置（当 USE_OPENAI_TTS_MODEL=true 时必选）
TTS_BASE_URL="http://localhost:5050/v1"    # OpenAI TTS 服务地址
TTS_API_KEY="your_tts_key"                 # OpenAI TTS API 密钥
TTS_MODEL="tts-1"                          # OpenAI TTS 模型

# 微软 TTS 配置（当 USE_OPENAI_TTS_MODEL=false 时可选）
HTTPS_PROXY="http://your-proxy:port"       # 代理服务器地址（非大陆地区可能需要）
```

### 语音配置（可选，已提供默认值）

```bash
# 中文主播音色
ANCHOR_TYPE_HOST_CN="zh-CN-XiaoxiaoNeural"   # 主持人
ANCHOR_TYPE_GUEST_CN="zh-CN-YunxiaNeural"    # 嘉宾

# 英文主播音色
ANCHOR_TYPE_HOST_EN="en-US-JennyNeural"      # 主持人
ANCHOR_TYPE_GUEST_EN="en-US-ChristopherNeural"  # 嘉宾
```

### 系统配置（可选，已提供默认值）

```bash
# 文件存储
TASK_DIR="./data/tasks"     # 任务文件目录
DB_PATH="./data/tasks.db"   # 数据库路径

# 服务配置
PORT=28811                  # 服务端口
HOST="0.0.0.0"             # 监听地址
```

## 🔌 API 接口

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/post_task` | 创建播客任务 |
| GET | `/api/get_task` | 获取任务状态 |
| GET | `/api/get_list` | 获取任务列表 |
| DELETE | `/api/delete_task/{task_id}` | 删除任务 |

> 📝 完整 API 文档请访问 `/docs` 端点


## 📁 项目结构

```
lingopod/
├── app/              # 核心应用目录
│   ├── server.py     # 核心逻辑
│   ├── api.py        # API 路由
│   ├── models.py     # 数据模型
│   └── config.py     # 配置文件
│   └── prompt_templates.yaml     # 提示词模板
├── static/           # 前端资源
├── main.py          # 入口文件
├── Dockerfile       # 容器配置
└── requirements.txt # 项目依赖
```

## 🤝 参与贡献

欢迎通过以下方式贡献：
- 🐛 报告问题
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码改进


## 📄 开源协议

本项目采用 [MIT 许可证](LICENSE) 开源。


## 🔗 相关项目

- [LingoPod 客户端](https://github.com/linshenkx/lingopod-client) - 跨平台客户端应用

