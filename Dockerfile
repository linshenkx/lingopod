# 使用多阶段构建
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装 chsrc 工具
RUN wget https://gitee.com/RubyMetric/chsrc/releases/download/pre/chsrc-x64-linux -O chsrc \
    && chmod +x ./chsrc

# 复制依赖文件
COPY requirements.txt .

# 配置镜像源
RUN ./chsrc set debian first && ./chsrc set python first

# 安装依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# 设置工作目录
WORKDIR /opt/lingopod

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用文件
COPY app ./app
COPY main.py ./
COPY static ./static

# 暴露端口
EXPOSE 28811

# 运行应用
CMD ["python", "main.py"]
