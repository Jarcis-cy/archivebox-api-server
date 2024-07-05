import subprocess
import os
import requests
from dotenv import load_dotenv
import re
import yaml

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


def execute_docker_compose_archivebox_command(command_args):
    """执行 Docker Compose ArchiveBox 命令并处理异常"""
    command = f"docker compose run archivebox {command_args}"
    try:
        subprocess.run(command, shell=True, check=True)
        return success_response(f"Command '{command}' executed successfully.")
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to execute command '{command}': {e}", error=e)


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

    if admin_username and admin_password:
        docker_compose['services']['archivebox']['environment'].append(f'ADMIN_USERNAME={admin_username}')
        docker_compose['services']['archivebox']['environment'].append(f'ADMIN_PASSWORD={admin_password}')

    if archivebox_version:
        docker_compose['services']['archivebox']['image'] = f'archivebox/archivebox:{archivebox_version}'

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


def remove_protocol(url):
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url


def extract_status(log_segment):
    return 'Failure' if 'Extractor failed' in log_segment else 'Success'


def parse_log(log_text, total_links):
    stripped_links = [remove_protocol(link) for link in total_links]

    result = {
        'status': 'Success',
        'links': []
    }

    for link in stripped_links:
        pattern = re.compile(r'\[\+\] .*?"{}"\s+(https?://[^\s]+)'.format(re.escape(link)))
        match = pattern.search(log_text)

        if match:
            start_pos = match.start()
            end_pos = log_text.find('\n[', start_pos)
            log_segment = log_text[start_pos:end_pos if end_pos != -1 else len(log_text)]

            status = extract_status(log_segment)
        else:
            status = 'Unknown'

        result['links'].append({
            'url': total_links[stripped_links.index(link)],
            'status': status
        })

    if any(link['status'] == 'Failure' for link in result['links']):
        result['status'] = 'Partial Success' if any(
            link['status'] == 'Success' for link in result['links']) else 'Failure'

    return result
