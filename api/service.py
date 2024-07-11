import json
import os
import subprocess
import requests
import yaml
from rest_framework import status

from api.utils import check_docker_version, check_docker_compose, execute_docker_compose_archivebox_command, \
    success_response, error_response, parse_log, clean_path, partial_success_response


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
        subprocess.run(up_command, shell=True, check=True, cwd=project_dir, encoding='utf-8')
        return success_response("ArchiveBox server started successfully.")
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to start ArchiveBox server: {e}", error=e)


def add_url(urls, tag, depth, update, update_all, overwrite, extractors, parser):
    # 构建 Docker Compose ArchiveBox 命令
    command_args = "add "

    if urls:
        command_args += " ".join(urls)
    if tag:
        command_args += f" --tag={','.join(tag)}"
    if depth is not None:
        command_args += f" --depth={depth}"
    if update:
        command_args += " --update"
    if update_all:
        command_args += " --update-all"
    if overwrite:
        command_args += " --overwrite"
    if extractors:
        if "headers" not in extractors:
            extractors += ",headers"
        command_args += f" --extract={extractors}"
    if parser:
        command_args += f" --parser={parser}"

    # 执行 Docker Compose ArchiveBox 命令
    result = execute_docker_compose_archivebox_command(command_args)
    if result["status"] == "error":
        return result

    log_text = result["stdout"]

    # 解析日志并获取存储路径
    print(log_text)
    archive_paths = parse_log(log_text, urls)

    # 获取 PROJECT_DIR
    project_dir = os.getenv('PROJECT_DIR')
    data_dir = os.path.join(project_dir, "data")

    # 构建结果字典和爬取状态字典
    url_archive_paths = {}
    crawl_status = {}

    for item in archive_paths:
        url = item['url']
        path = item['archive_path']
        full_path = os.path.join(data_dir, path)
        index_file = os.path.join(full_path, 'index.json')

        if not os.path.exists(index_file):
            crawl_status[url] = 'failed'
            continue

        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        history = index_data.get('history', {})
        if not history:
            crawl_status[url] = 'failed'
            continue

        if 'headers' not in history or not history["headers"] or history["headers"][0]["status"] != 'succeeded':
            crawl_status[url] = 'failed'
            continue

        url_paths = {}
        for key, entries in history.items():
            if entries and entries[0].get('status') == 'succeeded':
                output = entries[0].get('output')
                if output:
                    static_url = f"/static/{clean_path(os.path.join(path, output))}"
                    url_paths[key] = static_url

        if url_paths:
            url_archive_paths[url] = url_paths
            crawl_status[url] = 'succeeded'
        else:
            crawl_status[url] = 'failed'

    # 构建最终的响应内容
    success_urls = {url: paths for url, paths in url_archive_paths.items() if crawl_status[url] == 'succeeded'}
    failed_urls = [url for url in urls if crawl_status.get(url) == 'failed']

    if success_urls and failed_urls:
        return partial_success_response("URLs processed with some failures.", archive_paths=success_urls, failed_urls=failed_urls)
    elif success_urls:
        return success_response("All URLs processed successfully.", archive_paths=success_urls)
    else:
        return error_response("All URLs failed to process.", failed_urls=failed_urls)