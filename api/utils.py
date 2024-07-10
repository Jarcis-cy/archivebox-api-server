import subprocess

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


def remove_protocol(url):
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    return url


def extract_archive_path(log_segment):
    match = re.search(r'> (./archive/[^\s]+)', log_segment)
    return match.group(1) if match else None


def parse_log(log_text, total_links):
    stripped_links = [remove_protocol(link) for link in total_links]

    result = []

    for link in stripped_links:
        pattern = re.compile(r'\[\+\] .*?"{}"\s+(https?://[^\s]+)'.format(re.escape(link)))
        match = pattern.search(log_text)

        if match:
            start_pos = match.start()
            end_pos = log_text.find('\n[', start_pos)
            log_segment = log_text[start_pos:end_pos if end_pos != -1 else len(log_text)]

            archive_path = extract_archive_path(log_segment)
        else:
            archive_path = None

        result.append({
            'url': total_links[stripped_links.index(link)],
            'archive_path': archive_path
        })

    return result
