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

### 2. 安装开发依赖

```bash
# 安装依赖管理工具
pip install pip-tools

# 安装项目依赖
pip-sync
```

### 3. 配置开发环境变量
修改 `app/config.py` 文件，配置必要的环境变量

## 📦 依赖管理

项目使用 pip-tools 进行依赖管理，确保环境的一致性和可重现性。

### 依赖更新流程

1. **更新依赖**
   ```bash
   # 更新 requirements.txt
   pip-compile requirements.in --upgrade
   
   # 同步环境依赖
   pip-sync
   ```

2. **添加新依赖**
   ```bash
   # 编辑 requirements.in 添加新依赖
   echo "new-package==1.0.0" >> requirements.in
   
   # 重新生成 requirements.txt
   pip-compile requirements.in
   
   # 同步环境
   pip-sync
   ```

> 💡 **说明**:
> - `requirements.in`: 主要依赖配置文件
> - `requirements.txt`: 由 pip-compile 自动生成的完整依赖清单
> - 新增依赖请修改 `requirements.in` 文件，而不是直接修改 `requirements.txt`


## 🏗️ 构建与部署

### 本地开发运行
```bash
# 启动开发服务器
python main.py
```
### Docker 构建
```bash
# 构建镜像
docker build -t linshen/lingopod:latest .

```

