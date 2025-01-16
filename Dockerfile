# Python构建环境
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 chsrc 工具
RUN curl https://chsrc.run/posix | bash

# 配置镜像源
RUN chsrc set debian && chsrc set python

# 安装 Poetry
RUN pip install poetry && poetry config virtualenvs.create false

# 复制项目依赖文件
COPY pyproject.toml poetry.lock ./

# 安装依赖
RUN poetry install --only main --no-root

# 最终阶段
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 设置工作目录
WORKDIR /opt/lingopod

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# 复制应用文件和环境变量模板
COPY server ./server
COPY .env.template .env.template

# 创建环境变量文件
RUN cp .env.template .env

# 暴露端口
EXPOSE 28811

# 运行应用
CMD ["python", "server/run.py"]
