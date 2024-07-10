import os
import subprocess
import requests
import yaml

from api.utils import check_docker_version, check_docker_compose, execute_docker_compose_archivebox_command, \
    success_response, error_response


def initialize_archivebox():
    """初始化ArchiveBox"""

    project_dir = os.getenv('PROJECT_DIR')

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

    # 读取并修改 docker-compose.yml 文件
    with open(docker_compose_path, 'r') as file:
        docker_compose = yaml.safe_load(file)

    admin_username = os.getenv('ADMIN_USERNAME')
    admin_password = os.getenv('ADMIN_PASSWORD')
    archivebox_version = os.getenv('ARCHIVEBOX_VERSION')
    deployment_ports = os.getenv('DEPLOYMENT_PORTS')

    if admin_username and admin_password:
        docker_compose['services']['archivebox']['environment'].append(f'ADMIN_USERNAME={admin_username}')
        docker_compose['services']['archivebox']['environment'].append(f'ADMIN_PASSWORD={admin_password}')

    if archivebox_version:
        docker_compose['services']['archivebox']['image'] = f'archivebox/archivebox:{archivebox_version}'

    if deployment_ports:
        docker_compose['services']['archivebox']['ports'].append(deployment_ports)

    with open(docker_compose_path, 'w') as file:
        yaml.safe_dump(docker_compose, file)

    # 运行初始设置创建管理员用户
    init_result = execute_docker_compose_archivebox_command("init --setup")
    if init_result["status"] != "success":
        return init_result

    # 启动服务器
    up_command = "docker compose up -d"
    try:
        subprocess.run(up_command, shell=True, check=True)
        return success_response("ArchiveBox server started successfully.")
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to start ArchiveBox server: {e}", error=e)


def add_url(urls, tag, depth, update, update_all, overwrite, extractors, parser):
    pass
