import json
import os
import subprocess
from typing import List, Dict, Any
from dotenv import load_dotenv

import requests
import yaml

from api.utils import check_docker_version, check_docker_compose, execute_docker_compose_archivebox_command, \
    success_response, error_response, parse_log, clean_path, partial_success_response, save_result, save_tags, \
    build_add_args, process_archive_paths, build_response

load_dotenv()


def initialize_archivebox() -> Dict[str, Any]:
    project_dir = os.getenv('PROJECT_DIR')

    docker_version_result = check_docker_version()
    if docker_version_result["status"] != "success":
        return docker_version_result

    docker_compose_result = check_docker_compose()
    if docker_compose_result["status"] != "success":
        return docker_compose_result

    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    docker_compose_url = os.getenv('DOCKER_COMPOSE_URL', 'https://docker-compose.archivebox.io')
    docker_compose_path = os.path.join(project_dir, 'docker-compose.yml')
    proxy = os.getenv('PROXY')
    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        response = requests.get(docker_compose_url, proxies=proxies)
        response.raise_for_status()
        with open(docker_compose_path, 'wb') as file:
            file.write(response.content)
    except requests.RequestException as e:
        return error_response(f"Failed to download docker-compose.yml: {e}", error=e)

    with open(docker_compose_path, 'r') as file:
        docker_compose = yaml.safe_load(file)

    admin_username = os.getenv('ADMIN_USERNAME')
    admin_password = os.getenv('ADMIN_PASSWORD')
    archivebox_version = os.getenv('ARCHIVEBOX_VERSION')
    deployment_ports = os.getenv('DEPLOYMENT_PORTS')
    time_zones = os.getenv('TIME_ZONES')

    if admin_username and admin_password:
        docker_compose['services']['archivebox']['environment'].extend([
            f'ADMIN_USERNAME={admin_username}',
            f'ADMIN_PASSWORD={admin_password}'
        ])

    if time_zones:
        docker_compose['services']['archivebox']['environment'].append(f'TZ={time_zones}')

    if archivebox_version:
        docker_compose['services']['archivebox']['image'] = f'archivebox/archivebox:{archivebox_version}'

    if deployment_ports:
        docker_compose['services']['archivebox']['ports'].append(deployment_ports)

    with open(docker_compose_path, 'w') as file:
        yaml.safe_dump(docker_compose, file)

    init_result = execute_docker_compose_archivebox_command("init --setup")
    if init_result["status"] != "success":
        return init_result

    up_command = "docker compose up -d"
    try:
        subprocess.run(up_command, shell=True, check=True, cwd=project_dir, encoding='utf-8')
        return success_response("ArchiveBox server started successfully.")
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to start ArchiveBox server: {e}", error=e)


def add_url(urls: List[str], tags: List[str], depth: int, update: bool, update_all: bool, overwrite: bool,
            extractors: str, parser: str) -> Dict[str, Any]:
    command_args = build_add_args(urls, tags, depth, update, update_all, overwrite, extractors, parser)

    result = execute_docker_compose_archivebox_command(command_args)
    if result["status"] == "error":
        return result

    log_text = result["stdout"]
    archive_result = parse_log(log_text, urls)
    if archive_result["status"] == "error":
        return archive_result

    project_dir = os.getenv('PROJECT_DIR')
    data_dir = os.path.join(project_dir, "data")

    url_archive_paths, crawl_status = process_archive_paths(archive_result["data"], data_dir, tags)

    return build_response(urls, url_archive_paths, crawl_status)


def synchronize_local_data():
    project_dir = os.getenv('PROJECT_DIR')
