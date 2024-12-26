# 开发指南

## 🔧 本地开发

### 1. Conda 环境配置

```bash
# 创建 conda 环境
conda create -n lingopod python=3.11
conda activate lingopod

# 克隆项目
git clone https://github.com/linshenkx/lingopod.git
cd lingopod
```

### 2. 安装 Poetry 和项目依赖

```bash
# 安装 poetry
pip install poetry

# 配置 poetry 使用当前 conda 环境（可选）
poetry config virtualenvs.create false

# 安装项目依赖
poetry install
```

### 3. 配置开发环境变量
```bash
# 复制环境变量模板
cp .env.template .env

# 编辑 .env 文件，根据实际情况修改配置
vim .env 
```

> 💡 **说明**:
> - `.env.template` 包含了所有可配置的环境变量及其说明
> - `.env` 文件包含敏感信息，确保不要提交到版本控制系统
> - 生产环境建议使用系统环境变量而不是 `.env` 文件

### 4. 本地开发运行
```bash
# 启动开发服务器
poetry run python server/main.py
```

### 5. 依赖管理常用命令

1. **安装依赖**

```bash
# 安装所有依赖
poetry install

# 仅安装生产环境依赖
poetry install --no-dev
```

2. **添加新依赖**

```bash
# 添加生产依赖
poetry add package-name

# 添加开发依赖
poetry add --dev package-name
```

3. **更新依赖**

```bash
# 更新所有依赖
poetry update

# 更新指定依赖
poetry update package-name
```

4. **移除依赖**

```bash
poetry remove package-name
```

> 💡 **说明**:
> - `pyproject.toml`: 项目依赖配置文件
> - `poetry.lock`: 依赖版本锁定文件
> - 所有依赖管理都通过 poetry 命令进行，不要手动修改 lock 文件

## 🐳 Docker 镜像构建与发布

### 1. 构建 Docker 镜像
```bash
# 构建镜像
docker build -t linshen/lingopod:latest .
```

### 2. 标记和推送 Docker 镜像
```bash
# 标记镜像
docker tag linshen/lingopod:latest linshen/lingopod:3.0

# 推送镜像
docker push linshen/lingopod:3.0
docker push linshen/lingopod:latest

```

> 💡 **说明**:
> - 本地开发部分主要涉及环境配置和依赖管理，确保开发环境的一致性
> - Docker 镜像构建与发布部分则是为了将应用打包并发布到容器环境中，方便部署和扩展

