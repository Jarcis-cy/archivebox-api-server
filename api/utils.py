import json
import os
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urlparse
import pytz

from dotenv import load_dotenv
import re

from api.models import Result, Target, Tag, Tagging

# 加载 .env 文件中的配置
load_dotenv()


def success_response(message: str, **data: Any) -> Dict[str, Any]:
    return build_simple_response("success", message, **data)


def partial_success_response(message: str, **data: Any) -> Dict[str, Any]:
    return build_simple_response("partial_success", message, **data)


def error_response(message: str, error: Exception = None, **data: Any) -> Dict[str, Any]:
    return build_simple_response("error", message, error=error, **data)


def build_simple_response(status: str, message: str, error: Exception = None, **kwargs: Any) -> Dict[str, Any]:
    response = {
        "status": status,
        "message": message
    }
    if error:
        response["error"] = str(error)
    response.update(kwargs)
    return response


def clean_path(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/").replace("/./", "/")


def get_domain(url: str) -> str:
    return urlparse(url).netloc


def execute_docker_compose_archivebox_command(command_args: str) -> Dict[str, Any]:
    """执行 Docker Compose ArchiveBox 命令并处理异常"""
    project_dir = os.getenv('PROJECT_DIR')
    command = f"docker compose run --rm archivebox {command_args}"
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding='utf-8', cwd=project_dir)
        return success_response(f"Command '{command}' executed successfully.", stdout=result.stdout)
    except subprocess.CalledProcessError as e:
        return error_response(f"Failed to execute command '{command}': {e}", error=e, stderr=e.stderr)


def check_docker_version() -> Dict[str, Any]:
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
        return error_response(f"Error checking Docker version: {e}", error=e)


def check_docker_compose() -> Dict[str, Any]:
    try:
        subprocess.check_output(['docker', 'compose', 'version'], stderr=subprocess.STDOUT)
        return success_response("Docker Compose is available.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return error_response(f"Error checking Docker Compose: {e}", error=e)


def remove_protocol(url: str) -> str:
    return re.sub(r'^https?://', '', url).rstrip('/')


def extract_archive_path(log_segment: str) -> str:
    match = re.search(r'> (./archive/[^\s]+)', log_segment)
    return match.group(1) if match else None


def parse_log(log_text: str, total_links: List[str]) -> Dict[str, Any]:
    stripped_links = [remove_protocol(link) for link in total_links]
    result = []

    for link in stripped_links:
        pattern = re.compile(r'\[\+] .*?"{}"\s+(https?://\S+)'.format(re.escape(link)))
        match = pattern.search(log_text)
        if match:
            start_pos = match.start()
            end_pos = log_text.find('\n[', start_pos)
            log_segment = log_text[start_pos:end_pos if end_pos != -1 else len(log_text)]
            archive_path = extract_archive_path(log_segment)
        else:
            archive_path = None
        result.append({'url': total_links[stripped_links.index(link)], 'archive_path': archive_path})

    if not any(entry['archive_path'] for entry in result):
        return error_response(
            "The requested target already exists. If you want to update it, please add the update parameter.")

    return success_response("Log parsed successfully.", data=result)


def process_json_data(index_file: str) -> Dict[str, Any]:
    with open(index_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    url = data.get('url')
    timestamp = data.get('timestamp')
    history = data.get('history', {})
    shanghai_tz = pytz.timezone('Asia/Shanghai')

    processed_history = {}

    for key, value in history.items():
        start_ts = value[0].get('start_ts')
        end_ts = value[0].get('end_ts')

        if start_ts:
            utc_start_ts = datetime.fromisoformat(start_ts)
            beijing_start_ts = utc_start_ts.astimezone(shanghai_tz)
            start_ts = beijing_start_ts.strftime('%Y-%m-%d %H:%M:%S.%f')

        if end_ts:
            utc_end_ts = datetime.fromisoformat(end_ts)
            beijing_end_ts = utc_end_ts.astimezone(shanghai_tz)
            end_ts = beijing_end_ts.strftime('%Y-%m-%d %H:%M:%S.%f')

        processed_history[key] = {
            'start_ts': start_ts,
            'end_ts': end_ts,
            'status': True if value[0].get('status') == "succeeded" else False,
            'output': value[0].get('output')
        }

    return {
        'url': url,
        'timestamp': timestamp,
        'history': processed_history
    }


def save_result(index_file: str) -> Any:
    data = process_json_data(index_file)

    url = data['url']
    timestamp = data['timestamp']
    history = data['history']

    t, _ = Target.objects.get_or_create(url=url, defaults={
        'timestamp': timestamp,
        'domain': get_domain(url)
    })

    for key, value in history.items():
        start_ts = value.get('start_ts')
        end_ts = value.get('end_ts')

        Result.objects.create(
            timestamp=timestamp,
            start_ts=start_ts,
            end_ts=end_ts,
            status=value.get('status'),
            output=value.get('output'),
            target_id=t,
            extractor=key
        )

    return t


def save_tags(url: str, tags: List[str]) -> bool:
    target = Target.objects.get(url=url)

    for tag_name in tags:
        tag, _ = Tag.objects.get_or_create(name=tag_name)
        Tagging.objects.get_or_create(tag_id=tag, target_id=target)

    return True


def build_add_args(urls: List[str], tags: List[str], depth: int, update: bool, update_all: bool, overwrite: bool,
                   extractors: str, parser: str) -> str:
    command_args = "add "

    if urls:
        command_args += " ".join(urls)
    if tags:
        command_args += f" --tag={','.join(tags)}"
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

    return command_args


def process_archive_paths(archive_paths: List[Dict[str, Any]], data_dir: str, tags: List[str]) -> (
        Dict[str, Any], Dict[str, str]):
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

        save_result(index_file)

        if tags:
            save_tags(url, tags)

        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        history = index_data.get('history', {})
        if not history:
            crawl_status[url] = 'failed'
            continue

        if 'headers' not in history or not history["headers"] or history["headers"][0]["status"] != 'succeeded':
            crawl_status[url] = 'failed'
            continue

        url_paths = extract_url_paths(history, path)
        if url_paths:
            url_archive_paths[url] = url_paths
            crawl_status[url] = 'succeeded'
        else:
            crawl_status[url] = 'failed'

    return url_archive_paths, crawl_status


def extract_url_paths(history: Dict[str, Any], path: str) -> Dict[str, str]:
    url_paths = {}
    for key, entries in history.items():
        if entries and entries[0].get('status') == 'succeeded':
            output = entries[0].get('output')
            if output:
                static_url = f"/static/{clean_path(os.path.join(path, output))}"
                url_paths[key] = static_url
    return url_paths


def build_response(urls: List[str], url_archive_paths: Dict[str, Any], crawl_status: Dict[str, str]) -> Dict[str, Any]:
    success_urls = {url: paths for url, paths in url_archive_paths.items() if crawl_status[url] == 'succeeded'}
    failed_urls = [url for url in urls if crawl_status.get(url) == 'failed']

    if success_urls and failed_urls:
        return partial_success_response("URLs processed with some failures.", archive_paths=success_urls,
                                        failed_urls=failed_urls)
    elif success_urls:
        return success_response("All URLs processed successfully.", archive_paths=success_urls)
    else:
        return error_response("All URLs failed to process.", failed_urls=failed_urls)
