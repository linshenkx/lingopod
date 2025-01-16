# LingoPod (译播客) 🎙️

> 一款支持多平台的 AI 双语播客应用。支持RSS订阅和URL提交，将网页文章转换成您感兴趣的英语学习材料，并支持多级难度循序渐进学习。

## ✨ 主要特性

- 📱 多平台支持
  - Android 应用
  - Windows 客户端
  - Web 网页版
  - 完全开源代码
- 🤖 智能功能
  - 智能内容提取与总结
  - AI 驱动的自然对话生成
  - 高品质中英文 TTS
  - 自动生成双语字幕
  - 多级英语难度支持
    - 初级英语 (CEFR A2-B1, CET-4)
    - 中级英语 (CEFR B1-B2, CET-6)
    - 高级英语 (CEFR B2-C1, IELTS 6.5-7.5)
  - RSS 订阅支持
    - RSS 源管理与监控
    - 自动定时抓取更新
    - 智能增量更新检测
    - 个性化订阅配置
- 🎯 实用功能
  - 中英文音频切换
  - 智能音频处理
  - RESTful API 支持
  - 跨平台数据同步

## 🖼️ 界面预览

<div align="center">
  <img src="https://ghproxy.always200.com/https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/home-dark.jpg" width="45%" alt="主页深色模式"/>
  <img src="https://ghproxy.always200.com/https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/player-dark.jpg" width="45%" alt="播放器深色模式"/>
</div>

## ⚡️ 在线体验

您可以通过以下方式快速体验LingoPod:

### 主要入口
- 🌐 Web客户端: [client.lingopod.top](https://client.lingopod.top)
  - 用于生成和播放双语播客内容
  - 测试账号: test / test（注：仅供功能体验，有使用限制）

### 其他服务
- 📊 管理后台: [manager.lingopod.top](https://manager.lingopod.top)
  - 用于管理任务和查看系统状态
- 🔧 API服务: [server.lingopod.top](https://server.lingopod.top/api/v1/users/health)
  - RESTful API接口服务

## ⚙️ 使用须知

### 1. 内容支持范围
- 在线版本出于安全考虑，仅支持微信公众号文章（https://mp.weixin.qq.com）
- 自部署版本可配置支持任意网页内容

### 2. 试用服务说明
- 仅供功能体验和测试
- 服务可能随时调整，不保证数据持久化
- 生产环境建议自行部署

### 3. 部署配置说明
- 客户端与管理后台：
  - 支持独立部署
  - 默认API地址：https://server.lingopod.top
  - 支持在界面中切换自定义API地址
- 生产环境推荐：
  - 自行部署API服务
  - 可继续使用在线版客户端


## 🏗️ 技术架构

本项目采用前后端分离架构，包含以下核心组件：

- **API 服务端** ([lingopod](https://github.com/linshenkx/lingopod))
  - Python + FastAPI 构建 RESTful API
  - LangChain 内容处理与转换
  - Edge-TTS/OpenAI TTS 语音合成
  - FFmpeg 音频处理
  - 负责内容转换、播客生成、用户管理等核心功能

- **客户端应用** ([lingopod-client](https://github.com/linshenkx/lingopod-client))
  - Flutter 跨平台开发
  - Provider 状态管理
  - Just Audio 音频引擎
  - 支持 Android/Windows/Web
  - 负责播客播放、任务管理、RSS订阅等用户交互

- **管理后台** ([lingopod-manager](https://github.com/linshenkx/lingopod-manager))
  - React + TypeScript
  - Redux 状态管理
  - Ant Design + Material UI
  - 负责用户管理、任务监控、系统配置等运维功能

## 📱 客户端下载

您可以通过以下方式获取客户端：

- **Android APK**: [点击下载](https://ghproxy.always200.com/https://github.com/linshenkx/
lingopod-client/releases/latest/download/lingopod-android.apk)
- **Windows 客户端**: [点击下载](https://github.com/linshenkx/lingopod-client/releases/latest/
download/lingopod-windows.zip)
- **Web 版本**: [点击下载](https://github.com/linshenkx/lingopod-client/releases/latest/download/
lingopod-web.zip)

> 更多版本及历史更新请访问 [releases 页面](https://github.com/linshenkx/lingopod-client/releases)

## 外部依赖说明

项目依赖两个核心服务:
- **LLM 服务**: 通过 OpenAI 兼容接口对接,支持各类大语言模型，使用免费的 qwen2.5-7b 模型也可以达到较好效果
- **TTS 服务**: 支持两种模式：
  1. 微软 TTS（edge-tts）：默认模式，免费使用。非大陆地区需设置 HTTPS_PROXY 环境变量
  2. OpenAI TTS：通过设置 USE_OPENAI_TTS_MODEL=true 启用，需配置相应的 API

> 推荐参考 [edge-tts-openai-cf-worker](https://github.com/linshenkx/edge-tts-openai-cf-worker) 部署
基于 Cloudflare Workers 的免费 Edge OpenAI TTS 服务

## 🚀 快速开始

配置可通过 `.env` 文件或环境变量设置。详细配置说明请参考 [.env.template](https://github.com/linshenkx/
lingopod/main/.env.template)。

### 核心服务部署

#### Edge TTS 模式（默认）
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
     -e HTTPS_PROXY="http://your-proxy:7890" \
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

即可得到 API 基础地址：http://localhost:28811

## 📈 开发规划

1. 智能学习系统
   - 结合记忆曲线优化生词出现频率
   - 提供个性化学习建议
   - 完善生词本功能

2. 多端协同
   - 开发浏览器插件
   - 开发笔记软件插件
   - 打造无缝学习体验

3. 性能优化
   - 优化音频缓存策略
   - 提升内容转换速度
   - 改进数据同步机制

## 📖 文档

- [开发文档](https://github.com/linshenkx/lingopod/blob/main/README-dev.md)
- [API 文档](https://github.com/linshenkx/lingopod/blob/main/docs/api/README.md)
- [项目结构](https://github.com/linshenkx/lingopod/blob/main/docs/structure.md)
- [功能设计](https://github.com/linshenkx/lingopod/blob/main/docs/design.md)

## 🤝 贡献指南

欢迎通过以下方式参与项目：
- 提交 Issue 报告问题
- 提出新功能建议
- 改进文档
- 提交 Pull Request

## 📄 开源协议

本项目采用 [MIT 许可证](LICENSE) 开源。

## 🔗 相关项目

- [LingoPod 客户端](https://github.com/linshenkx/lingopod-client) - 跨平台客户端应用
- [LingoPod 管理后台](https://github.com/linshenkx/lingopod-manager) - 任务和系统管理
- [LingoPod 官网](https://github.com/linshenkx/lingopod-web) - 官网展示
- [edge-tts-openai-cf-worker](https://github.com/linshenkx/edge-tts-openai-cf-worker) - 基于 Cloudflare Workers 的免费 OpenAI TTS 服务
