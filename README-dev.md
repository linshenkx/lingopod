# 开发指南

## 🔧 本地开发环境配置

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
修改 `app/config.py` 文件，配置必要的环境变量

## 📦 依赖管理

项目使用 Poetry 进行依赖管理，确保环境的一致性和可重现性。

### 依赖管理常用命令

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

## 🏗️ 构建与部署

### 本地开发运行
```bash
# 启动开发服务器
poetry run python server/main.py
```

### Docker 构建
```bash
# 构建镜像
docker build -t linshen/lingopod:latest .
docker tag linshen/lingopod:latest linshen/lingopod:2.0
docker push linshen/lingopod:2.0
docker push linshen/lingopod:latest

```

