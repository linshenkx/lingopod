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
- **TTS 服务**: 支持标准 OpenAI TTS API,可选用以下方案:
  - OpenAI 官方 TTS
  - [openai-edge-tts](https://github.com/travisvn/openai-edge-tts) (推荐,免费使用微软 TTS)
  - 其他兼容 OpenAI API 的 TTS 服务

### 1. TTS 服务配置（可选）

```bash
# 启动 TTS 服务
# 这里API_KEY可以随意设置，后续核心服务需要根据此API_KEY调用TTS服务
docker run -d \
  --name tts \
  --restart always \
  -p 5050:5050 \
  -e API_KEY=abc \
  -e PORT=5050 \
  travisvn/openai-edge-tts:latest

# 验证服务
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer abc" \
  -d '{
    "model": "tts-1",
    "input": "Hello, I am your AI assistant! 我是你的AI助手！",
    "voice": "zh-CN-YunxiNeural"
  }' \
  --output speech.mp3
```

### 2. 核心服务部署

1. 创建数据目录：
```bash
mkdir -p /path/to/lingopod/data
```

2. 启动容器：
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
  -e TTS_BASE_URL=your_tts_base_url \
  -e TTS_API_KEY=your_tts_api_key \
  -e TTS_MODEL=your_tts_model \
  linshen/lingopod:latest
```

访问服务： http://localhost:28811 

容器管理：
```bash
# 查看容器日志
docker logs -f lingopod

# 停止并删除容器
docker stop lingopod && docker rm lingopod
```


### 3. 本地环境配置（建议优先docker）

1. 环境准备：
```bash
# 克隆项目
git clone https://github.com/linshenkx/lingopod.git
cd lingopod

# 安装依赖（建议python版本3.11）
pip install -r requirements.txt

# 启动服务
python main.py
```

## ⚙️ 配置说明

配置可通过config.py或环境变量设置，主要配置项包括：

### 核心服务配置

```bash
# LLM 服务配置
API_BASE_URL="https://api.example.com/v1"  # LLM API 基础地址
API_KEY="your_api_key"                     # API 密钥
MODEL="Qwen/Qwen2.5-7B-Instruct"          # 使用的模型

# TTS 服务配置
TTS_BASE_URL="http://localhost:5050/v1"    # TTS 服务地址
TTS_API_KEY="your_tts_key"                 # TTS API 密钥
TTS_MODEL="tts-1"                          # TTS 模型
```

### 语音配置

```bash
# 中文主播音色
ANCHOR_TYPE_HOST_CN="zh-CN-XiaoxiaoNeural"   # 主持人
ANCHOR_TYPE_GUEST_CN="zh-CN-YunxiaNeural"  # 嘉宾

# 英文主播音色
ANCHOR_TYPE_HOST_EN="en-US-JennyNeural"    # 主持人
ANCHOR_TYPE_GUEST_EN="en-US-ChristopherNeural"  # 嘉宾
```

### 系统配置

```bash
# 文件存储
TASK_DIR="./data/tasks"     # 任务文件目录
DB_PATH="./data/tasks.db"   # 数据库路径

# 服务配置
PORT=28811                     # 服务端口
HOST="0.0.0.0"                # 监听地址
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

