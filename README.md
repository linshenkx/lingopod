# LingoPod (译播客) 🎙️

> 开源的智能双语播客生成工具 - 将网页内容转化为沉浸式英语学习体验

## 📖 简介

LingoPod 是一个开源项目，旨在将网页内容转换为双语播客。它自动生成中英文音频和字幕，为内容创作者和语言学习者提供一站式解决方案。

## ✨ 核心特性

- 🤖 智能内容提取与总结
- 💬 AI 驱动的自然对话生成
- 🗣️ 高品质中英文 TTS
- 📝 自动生成双语字幕
- 🔄 中英文音频切换
- 🎵 智能音频处理
- 🚀 RESTful API 支持
- 📱 跨平台支持

<div align="center">
  <img src="https://ghproxy.always200.com/https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/home-dark.png" width="45%" alt="主页深色模式"/>
  <img src="https://ghproxy.always200.com/https://raw.githubusercontent.com/linshenkx/lingopod-client/main/images/player-dark.png" width="45%" alt="播放器深色模式"/>
</div>

## 🎯 项目架构

本项目包含以下组件：

- **API 服务端**：[lingopod](https://github.com/linshenkx/lingopod) - 提供核心 RESTful API
- **客户端应用**：[lingopod-client](https://github.com/linshenkx/lingopod-client) - 支持 Android/Web/Windows
- **管理后台**：[lingopod-manager](https://github.com/linshenkx/lingopod-manager) - 任务和系统管理
- **官网**：[lingopod-web](https://github.com/linshenkx/lingopod-web)

## 📱 客户端下载

您可以通过以下方式获取客户端：

- **Android APK**: [点击下载](https://ghproxy.always200.com/https://github.com/linshenkx/lingopod-client/releases/latest/download/lingopod-android.apk)
- **Windows 客户端**: [点击下载](https://github.com/linshenkx/lingopod-client/releases/latest/download/lingopod-windows.zip)
- **Web 版本**: [点击下载](https://github.com/linshenkx/lingopod-client/releases/latest/download/lingopod-web.zip)

> 更多版本及历史更新请访问 [releases 页面](https://github.com/linshenkx/lingopod-client/releases)

### 在线演示

- Web客户端：[client.lingopod.top](https://client.lingopod.top) : 建议使用用户名test，密码test
- 管理后台：[manager.lingopod.top](https://manager.lingopod.top)
- API 服务：[server.lingopod.top](https://server.lingopod.top)

> **注意**: [https://server.lingopod.top](https://server.lingopod.top) 仅提供有限试用，只支持微信公众号文章链接转换为播客，不保证运行稳定性，随时可能删除数据/停止服务，请勿用于重要场景，建议自行部署。

## ⚙️ 部署说明

客户端和后台管理界面均可自行部署，且可在界面修改 API 服务地址。目前默认使用的是 [https://server.lingopod.top](https://server.lingopod.top)。客户端和后台管理界面是无状态的，只需要部署自己的 API 服务，然后在客户端切换 API 地址即可。

## API 依赖说明

项目依赖两个核心服务:
- **LLM 服务**: 通过 OpenAI 兼容接口对接,支持各类大语言模型，使用免费的 qwen2.5-7b 模型也可以达到较好效果
- **TTS 服务**: 支持两种模式：
  1. 微软 TTS（edge-tts）：默认模式，免费使用。非大陆地区需设置 HTTPS_PROXY 环境变量
  2. OpenAI TTS：通过设置 USE_OPENAI_TTS_MODEL=true 启用，需配置相应的 API

> 推荐参考 [edge-tts-openai-cf-worker](https://github.com/linshenkx/edge-tts-openai-cf-worker) 部署基于 Cloudflare Workers 的免费 Edge OpenAI TTS 服务

## 🚀 快速开始

配置可通过 `.env` 文件或环境变量设置。详细配置说明请参考 [.env.template](https://github.com/linshenkx/lingopod/main/.env.template)。

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

## 📖 文档

- [开发文档](https://github.com/linshenkx/lingopod/main/README-dev.md)
- [API 文档](https://github.com/linshenkx/lingopod/main/docs/api.md)
- [项目结构](https://github.com/linshenkx/lingopod/main/docs/structure.md)
- [设计原则](https://github.com/linshenkx/lingopod/main/docs/design.md)

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
