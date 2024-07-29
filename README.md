# ArchiveBox-API-Server

因为ArchiveBox本身的API存在一些Bug，使用起来也不便捷，故二开一个项目，通过api控制ArchiveBox

## 实现方式

通过docker compose拉取archivebox，然后使用docker compose命令调用使用

## 部署方式

### 1. 安装docker

<details>
<summary>在 Linux 上安装最新版 Docker</summary>

#### 1. 更新包索引

```bash
sudo apt-get update
```

#### 2. 安装必要的依赖包
```bash
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

#### 3. 添加 Docker 的官方 GPG 密钥
```bash
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

#### 4. 设置 Docker 的存储库
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

#### 5. 更新包索引
```bash
sudo apt-get update
```

#### 6. 安装 Docker 引擎
```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

#### 7. 启动 Docker 并将其设置为开机自启
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

#### 8. 验证安装
```bash
sudo docker run hello-world
```
</details>

<details><summary>在 Windows 上安装最新版 Docker</summary>

#### 1. 下载 Docker Desktop
前往 Docker 官方网站，下载最新版本的 Docker Desktop 安装程序：
[Docker Desktop 下载页面](https://www.docker.com/products/docker-desktop)

#### 2. 运行安装程序
双击下载的 Docker Desktop 安装程序，按照安装向导的提示完成安装。

#### 3. 配置 WSL 2（可选，但推荐）
Docker Desktop 需要 WSL 2 支持，以提升性能和兼容性。如果你的 Windows 版本支持 WSL 2，请按照以下步骤进行配置：

1. 启用 WSL
    ```powershell
    wsl --install
    ```

2. 设置 WSL 2 为默认版本
    ```powershell
    wsl --set-default-version 2
    ```

3. 安装一个 Linux 发行版（如 Ubuntu）从 Microsoft Store。

#### 4. 启动 Docker Desktop
安装完成后，启动 Docker Desktop。首次启动可能会提示你进行一些配置，比如是否使用 WSL 2 作为后端。

#### 5. 验证安装
打开一个命令提示符或 PowerShell，运行以下命令：
```powershell
docker run hello-world
```

如果看到 Docker 成功运行并输出相关信息，则说明安装成功。

</details>

### 2. 初始化项目

```bash
# 克隆项目代码
cd archivebox-api-server

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux 或 macOS
source venv/bin/activate

# 安装项目依赖
pip install -r requirements.txt

# 配置环境变量
mv .env.example .env

# 进行数据库迁移
python manage.py migrate

# 创建超级用户（可选）
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver
```

## 使用方式

可以在启动服务器后，查看:
- `http://127.0.0.1:8000/swagger/`
- `http://127.0.0.1:8000/redoc/`

看文档描述即可

**需要先使用init，将指定版本的archivebox的容器启动起来，然后再进行后续操作**

## 注意

本项目没有设置任何的认证相关的限制，仅作为便于使用的api server，如果部署在公网，务必使用nginx等设置访问白名单