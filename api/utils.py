import subprocess
import os
import requests
from dotenv import load_dotenv
import re

# 加载 .env 文件中的配置
load_dotenv()


def success_response(message, **data):
    response = {
        "status": "success",
        "message": message
    }
    response.update(data)
    return response


def error_response(message, error=None, **data):
    response = {
        "status": "error",
        "message": message
    }
    if error:
        response["error"] = str(error)
    response.update(data)
    return response


def check_docker_version():
    try:
        output = subprocess.check_output(['docker', '--version'], stderr=subprocess.STDOUT)
        version_match = re.search(r'Docker version (\d+\.\d+\.\d+)', output.decode('utf-8'))
        if version_match:
            version = version_match.group(1)
            major, minor, patch = map(int, version.split('.'))
            if (major > 17) or (major == 17 and minor >= 6):
                return success_response(f"Docker version {version} is sufficient.", version=version)
            else:
                return error_response(
                    f"Docker version {version} is not sufficient. Please upgrade to 17.06.0 or later.", version=version)
        else:
            return error_response("Failed to parse Docker version.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return error_response(f"Error checking Docker version: {e}")


def check_docker_compose():
    try:
        subprocess.check_output(['docker', 'compose', 'version'], stderr=subprocess.STDOUT)
        return success_response("Docker Compose is available.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return error_response(f"Error checking Docker Compose: {e}")


def initialize_archivebox(project_dir):
    # 预检查 Docker 和 Docker Compose
    docker_version_result = check_docker_version()
    if docker_version_result["status"] != "success":
        return docker_version_result

    docker_compose_result = check_docker_compose()
    if docker_compose_result["status"] != "success":
        return docker_compose_result

    # 创建项目目录
    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    os.chdir(project_dir)

    # 下载 docker-compose.yml 文件
    docker_compose_url = os.getenv('DOCKER_COMPOSE_URL', 'https://docker-compose.archivebox.io')
    docker_compose_path = os.path.join(project_dir, 'docker-compose.yml')
    proxy = os.getenv('PROXY')

    proxies = {
        "http": proxy,
        "https": proxy
    } if proxy else None

    try:
        response = requests.get(docker_compose_url, proxies=proxies)
        response.raise_for_status()
        with open(docker_compose_path, 'wb') as file:
            file.write(response.content)
    except requests.RequestException as e:
        return error_response(f"Failed to download docker-compose.yml: {e}", error=e)

    # 运行初始设置创建管理员用户
    init_command = "docker compose run archivebox init --setup"

    try:
        subprocess.run(init_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to initialize ArchiveBox: {e}", error=e)

    # 启动服务器
    up_command = "docker compose up -d"

    try:
        subprocess.run(up_command, shell=True, check=True)
        return success_response("ArchiveBox server started successfully.")
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to start ArchiveBox server: {e}", error=e)
