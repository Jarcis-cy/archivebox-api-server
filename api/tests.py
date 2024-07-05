import unittest
from unittest.mock import patch, MagicMock

import requests

from api.utils import check_docker_version, check_docker_compose, initialize_archivebox, parse_log


class TestInitArchiveBox(unittest.TestCase):

    @patch('api.utils.subprocess.check_output')
    def test_check_docker_version_sufficient(self, mock_check_output):
        mock_check_output.return_value = b"Docker version 20.10.7, build f0df350"
        result = check_docker_version()
        self.assertEqual(result["status"], "success")
        self.assertIn("Docker version 20.10.7 is sufficient.", result["message"])
        self.assertEqual(result["version"], "20.10.7")

    @patch('api.utils.subprocess.check_output')
    def test_check_docker_version_insufficient(self, mock_check_output):
        mock_check_output.return_value = b"Docker version 17.05.0, build 89658be"
        result = check_docker_version()
        self.assertEqual(result["status"], "error")
        self.assertIn("Docker version 17.05.0 is not sufficient.", result["message"])
        self.assertEqual(result["version"], "17.05.0")

    @patch('api.utils.subprocess.check_output')
    def test_check_docker_version_parse_failure(self, mock_check_output):
        mock_check_output.return_value = b"invalid output"
        result = check_docker_version()
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to parse Docker version.", result["message"])

    @patch('api.utils.subprocess.check_output', side_effect=FileNotFoundError())
    def test_check_docker_version_not_installed(self, mock_check_output):
        result = check_docker_version()
        self.assertEqual(result["status"], "error")
        self.assertIn("Error checking Docker version:", result["message"])

    @patch('api.utils.subprocess.check_output')
    def test_check_docker_compose_available(self, mock_check_output):
        mock_check_output.return_value = b"Docker Compose version 1.29.2, build 5becea4c"
        result = check_docker_compose()
        self.assertEqual(result["status"], "success")
        self.assertIn("Docker Compose is available.", result["message"])

    @patch('api.utils.subprocess.check_output', side_effect=FileNotFoundError())
    def test_check_docker_compose_not_installed(self, mock_check_output):
        result = check_docker_compose()
        self.assertEqual(result["status"], "error")
        self.assertIn("Error checking Docker Compose:", result["message"])

    @patch('api.utils.requests.get')
    @patch('api.utils.subprocess.run')
    @patch('api.utils.check_docker_compose')
    @patch('api.utils.check_docker_version')
    @patch('api.utils.os.makedirs')
    @patch('api.utils.os.path.exists', return_value=False)
    def test_initialize_archivebox_successful(self, mock_exists, mock_makedirs, mock_check_docker_version,
                                              mock_check_docker_compose, mock_run, mock_get):
        mock_check_docker_version.return_value = {
            "status": "success",
            "message": "Docker version is sufficient.",
            "version": "20.10.7"
        }
        mock_check_docker_compose.return_value = {
            "status": "success",
            "message": "Docker Compose is available."
        }
        mock_get.return_value = MagicMock(status_code=200, content=b'docker-compose content')
        mock_run.side_effect = [
            MagicMock(returncode=0),  # init command
            MagicMock(returncode=0)  # up command
        ]

        result = initialize_archivebox('/fake/project/dir')
        self.assertEqual(result["status"], "success")
        self.assertIn("ArchiveBox server started successfully.", result["message"])

        mock_exists.assert_called_once_with('/fake/project/dir')
        mock_makedirs.assert_called_once_with('/fake/project/dir')
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_run.call_count, 2)

    @patch('api.utils.subprocess.run')
    @patch('api.utils.check_docker_compose')
    @patch('api.utils.check_docker_version')
    def test_initialize_archivebox_docker_version_failure(self, mock_check_docker_version, mock_check_docker_compose,
                                                          mock_run):
        mock_check_docker_version.return_value = {
            "status": "error",
            "message": "Docker version is insufficient."
        }

        result = initialize_archivebox('/fake/project/dir')
        self.assertEqual(result["status"], "error")
        self.assertIn("Docker version is insufficient.", result["message"])

        mock_check_docker_version.assert_called_once()
        mock_check_docker_compose.assert_not_called()
        mock_run.assert_not_called()

    @patch('api.utils.subprocess.run')
    @patch('api.utils.check_docker_compose')
    @patch('api.utils.check_docker_version')
    def test_initialize_archivebox_docker_compose_failure(self, mock_check_docker_version, mock_check_docker_compose,
                                                          mock_run):
        mock_check_docker_version.return_value = {
            "status": "success",
            "message": "Docker version is sufficient."
        }
        mock_check_docker_compose.return_value = {
            "status": "error",
            "message": "Docker Compose is not available."
        }

        result = initialize_archivebox('/fake/project/dir')
        self.assertEqual(result["status"], "error")
        self.assertIn("Docker Compose is not available.", result["message"])

        mock_check_docker_version.assert_called_once()
        mock_check_docker_compose.assert_called_once()
        mock_run.assert_not_called()

    @patch('api.utils.requests.get', side_effect=requests.RequestException('Curl error'))
    @patch('api.utils.subprocess.run')
    @patch('api.utils.check_docker_compose')
    @patch('api.utils.check_docker_version')
    def test_initialize_archivebox_curl_failure(self, mock_check_docker_version, mock_check_docker_compose, mock_run,
                                                mock_get):
        mock_check_docker_version.return_value = {
            "status": "success",
            "message": "Docker version is sufficient."
        }
        mock_check_docker_compose.return_value = {
            "status": "success",
            "message": "Docker Compose is available."
        }

        result = initialize_archivebox('/fake/project/dir')
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to download docker-compose.yml:", result["message"])

        mock_get.assert_called_once()
        mock_run.assert_not_called()


class FormatOutputTest(unittest.TestCase):

    def setUp(self):
        self.single_target_success = """
[i] [2024-07-04 06:16:07] ArchiveBox v0.7.2: archivebox add --depth=0 https://www.baidu.com/ --extract title,screenshot
    > /data

[+] [2024-07-04 06:16:09] Adding 1 links to index (crawl depth=0)...
    > Saved verbatim input to sources/1720073769-import.txt
    > Parsed 1 URLs from input (Generic TXT)
    > Found 1 new URLs not already in index

[*] [2024-07-04 06:16:09] Writing 1 links to main index...
    √ ./index.sqlite3

[*] [2024-07-04 06:16:09] Archiving 1/5 URLs from added set...

[▶] [2024-07-04 06:16:09] Starting archiving of 1 snapshots in index...

[+] [2024-07-04 06:16:09] "www.baidu.com"
    https://www.baidu.com/
    > ./archive/1720073769.137125
      > screenshot
      > title
        3 files (312.3 KB) in 0:00:04s

[√] [2024-07-04 06:16:13] Update of 1 pages complete (4.22 sec)
    - 0 links skipped
    - 1 links updated
    - 0 links had errors

    Hint: To manage your archive in a Web UI, run:
        archivebox server 0.0.0.0:8000
"""

        self.multiple_targets_success = """
[i] [2024-07-04 06:26:40] ArchiveBox v0.7.2: archivebox add --depth=0 https://cxsecurity.com/cveshow/CVE-2022-34593/ https://github.com/Liyou-ZY/POC/issues/1 --extract title,screenshot
    > /data

[+] [2024-07-04 06:26:42] Adding 2 links to index (crawl depth=0)...
    > Saved verbatim input to sources/1720074402-import.txt
    > Parsed 2 URLs from input (Generic TXT)
    > Found 2 new URLs not already in index

[*] [2024-07-04 06:26:42] Writing 2 links to main index...
    √ ./index.sqlite3

[*] [2024-07-04 06:26:42] Archiving 2/7 URLs from added set...

[▶] [2024-07-04 06:26:42] Starting archiving of 2 snapshots in index...

[+] [2024-07-04 06:26:42] "github.com/Liyou-ZY/POC/issues/1"
    https://github.com/Liyou-ZY/POC/issues/1
    > ./archive/1720074402.409769
      > screenshot
      > title
        3 files (347.8 KB) in 0:00:08s

[+] [2024-07-04 06:26:50] "cxsecurity.com/cveshow/CVE-2022-34593"
    https://cxsecurity.com/cveshow/CVE-2022-34593/
    > ./archive/1720074402.409496
      > screenshot
      > title
        3 files (1.2 MB) in 0:00:22s

[√] [2024-07-04 06:27:13] Update of 2 pages complete (31.04 sec)
    - 0 links skipped
    - 2 links updated
    - 0 links had errors

    Hint: To manage your archive in a Web UI, run:
        archivebox server 0.0.0.0:8000
"""

        self.single_target_failure = """
[i] [2024-07-04 04:09:39] ArchiveBox v0.7.2: archivebox add --depth=1 https://asdjfhkawkisejuhdfcvhbiuewsa.com/ --extract pdf,title,screenshot
    > /data

[+] [2024-07-04 04:09:40] Adding 1 links to index (crawl depth=1)...
    > Saved verbatim input to sources/1720066180-import.txt
    > Parsed 1 URLs from input (Generic TXT)

[*] Starting crawl of 1 sites 1 hop out from starting point
    > Downloading https://asdjfhkawkisejuhdfcvhbiuewsa.com/ contents
[!] Failed to download https://asdjfhkawkisejuhdfcvhbiuewsa.com/

     HTTPSConnectionPool(host='asdjfhkawkisejuhdfcvhbiuewsa.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7f2e349e5110>: Failed to resolve 'asdjfhkawkisejuhdfcvhbiuewsa.com' ([Errno -2] Name or service not known)"))
[!] Failed to get contents of URL {new_link.url} HTTPSConnectionPool(host='asdjfhkawkisejuhdfcvhbiuewsa.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7f2e349e5110>: Failed to resolve 'asdjfhkawkisejuhdfcvhbiuewsa.com' ([Errno -2] Name or service not known)"))
    > Found 1 new URLs not already in index

[*] [2024-07-04 04:09:41] Writing 1 links to main index...
    √ ./index.sqlite3

[*] [2024-07-04 04:09:41] Archiving 1/4 URLs from added set...

[▶] [2024-07-04 04:09:41] Starting archiving of 1 snapshots in index...

[+] [2024-07-04 04:09:41] "asdjfhkawkisejuhdfcvhbiuewsa.com"
    https://asdjfhkawkisejuhdfcvhbiuewsa.com/
    > ./archive/1720066180.764635
      > pdf
      > screenshot
      > title
        Extractor failed:
            ConnectionError HTTPSConnectionPool(host='asdjfhkawkisejuhdfcvhbiuewsa.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7f2e34732cd0>: Failed to resolve 'asdjfhkawkisejuhdfcvhbiuewsa.com' ([Errno -2] Name or service not known)"))
        Run to see full output:
          docker run -it -v $PWD/data:/data archivebox/archivebox /bin/bash
            cd /data/archive/1720066180.764635;
            curl --silent --location --compressed --max-time 60 --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 ArchiveBox/0.7.2 (+https://github.com/ArchiveBox/ArchiveBox/) curl/curl 8.5.0 (x86_64-pc-linux-gnu)" "https://asdjfhkawkisejuhdfcvhbiuewsa.com/"

        4 files (303.9 KB) in 0:00:01s

[√] [2024-07-04 04:09:43] Update of 1 pages complete (2.02 sec)
    - 0 links skipped
    - 1 links updated
    - 1 links had errors

    Hint: To manage your archive in a Web UI, run:
        archivebox server 0.0.0.0:8000
"""

        self.multiple_targets_failure = """
[i] [2024-07-04 06:31:23] ArchiveBox v0.7.2: archivebox add --depth=0 https://sfdgcxsecurityasdfawefwAed.com/ https://afwegithubasdfasdfs.com/ --extract title,screenshot
    > /data

[+] [2024-07-04 06:31:24] Adding 2 links to index (crawl depth=0)...
    > Saved verbatim input to sources/1720074684-import.txt
    > Parsed 2 URLs from input (Generic TXT)
    > Found 2 new URLs not already in index

[*] [2024-07-04 06:31:24] Writing 2 links to main index...
    √ ./index.sqlite3

[*] [2024-07-04 06:31:24] Archiving 2/9 URLs from added set...

[▶] [2024-07-04 06:31:24] Starting archiving of 2 snapshots in index...

[+] [2024-07-04 06:31:24] "sfdgcxsecurityasdfawefwAed.com"
    https://sfdgcxsecurityasdfawefwAed.com/
    > ./archive/1720074684.657112
      > screenshot
      > title
        Extractor failed:
            ConnectionError HTTPSConnectionPool(host='sfdgcxsecurityasdfawefwaed.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7fae3bef1c10>: Failed to resolve 'sfdgcxsecurityasdfawefwaed.com' ([Errno -2] Name or service not known)"))
        Run to see full output:
          docker run -it -v $PWD/data:/data archivebox/archivebox /bin/bash
            cd /data/archive/1720074684.657112;
            curl --silent --location --compressed --max-time 60 --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 ArchiveBox/0.7.2 (+https://github.com/ArchiveBox/ArchiveBox/) curl/curl 8.5.0 (x86_64-pc-linux-gnu)" "https://sfdgcxsecurityasdfawefwAed.com/"

        3 files (279.6 KB) in 0:00:01s

[+] [2024-07-04 06:31:26] "afwegithubasdfasdfs.com"
    https://afwegithubasdfasdfs.com/
    > ./archive/1720074684.657393
      > screenshot
      > title
        Extractor failed:
            ConnectionError HTTPSConnectionPool(host='afwegithubasdfasdfs.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7fae3bc9c710>: Failed to resolve 'afwegithubasdfasdfs.com' ([Errno -2] Name or service not known)"))
        Run to see full output:
          docker run -it -v $PWD/data:/data archivebox/archivebox /bin/bash
            cd /data/archive/1720074684.657393;
            curl --silent --location --compressed --max-time 60 --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 ArchiveBox/0.7.2 (+https://github.com/ArchiveBox/ArchiveBox/) curl/curl 8.5.0 (x86_64-pc-linux-gnu)" "https://afwegithubasdfasdfs.com/"

        3 files (273.4 KB) in 0:00:01s

[√] [2024-07-04 06:31:27] Update of 2 pages complete (2.61 sec)
    - 0 links skipped
    - 2 links updated
    - 2 links had errors

    Hint: To manage your archive in a Web UI, run:
        archivebox server 0.0.0.0:8000
"""

        self.mixed_targets = """
[i] [2024-07-04 06:45:19] ArchiveBox v0.7.2: archivebox add --depth=0 https://docs.xray.cool https://asedfawecdwsac.caedws --extract title,screenshot
    > /data

[+] [2024-07-04 06:45:21] Adding 2 links to index (crawl depth=0)...
    > Saved verbatim input to sources/1720075521-import.txt
    > Parsed 2 URLs from input (Generic TXT)
    > Found 2 new URLs not already in index

[*] [2024-07-04 06:45:21] Writing 2 links to main index...
    √ ./index.sqlite3

[*] [2024-07-04 06:45:21] Archiving 2/11 URLs from added set...

[▶] [2024-07-04 06:45:21] Starting archiving of 2 snapshots in index...

[+] [2024-07-04 06:45:21] "docs.xray.cool"
    https://docs.xray.cool
    > ./archive/1720075521.41685
      > screenshot
      > title
        3 files (540.3 KB) in 0:00:04s

[+] [2024-07-04 06:45:26] "asedfawecdwsac.caedws"
    https://asedfawecdwsac.caedws
    > ./archive/1720075521.417146
      > screenshot
      > title
        Extractor failed:
            ConnectionError HTTPSConnectionPool(host='asedfawecdwsac.caedws', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x7f68be631f10>: Failed to resolve 'asedfawecdwsac.caedws' ([Errno -2] Name or service not known)"))
        Run to see full output:
          docker run -it -v $PWD/data:/data archivebox/archivebox /bin/bash
            cd /data/archive/1720075521.417146;
            curl --silent --location --compressed --max-time 60 --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 ArchiveBox/0.7.2 (+https://github.com/ArchiveBox/ArchiveBox/) curl/curl 8.5.0 (x86_64-pc-linux-gnu)" "https://asedfawecdwsac.caedws"

        3 files (272.7 KB) in 0:00:01s

[√] [2024-07-04 06:45:27] Update of 2 pages complete (5.92 sec)
    - 0 links skipped
    - 2 links updated
    - 1 links had errors

    Hint: To manage your archive in a Web UI, run:
        archivebox server 0.0.0.0:8000
"""

    def test_single_target_success(self):
        targets = ["https://www.baidu.com/"]
        expected_output = {
            'links': [
                {'status': 'Success', 'url': 'https://www.baidu.com/'}
            ],
            'status': 'Success'
        }
        result = parse_log(self.single_target_success, targets)
        self.assertDictEqual(result, expected_output)

    def test_multiple_targets_success(self):
        targets = ["https://cxsecurity.com/cveshow/CVE-2022-34593/", "https://github.com/Liyou-ZY/POC/issues/1"]
        expected_output = {
            'links': [
                {'status': 'Success', 'url': 'https://cxsecurity.com/cveshow/CVE-2022-34593/'},
                {'status': 'Success', 'url': 'https://github.com/Liyou-ZY/POC/issues/1'}
            ],
            'status': 'Success'
        }
        result = parse_log(self.multiple_targets_success, targets)
        self.assertDictEqual(result, expected_output)

    def test_single_target_failure(self):
        targets = ["https://asdjfhkawkisejuhdfcvhbiuewsa.com/"]
        expected_output = {
            'links': [
                {'status': 'Failure', 'url': 'https://asdjfhkawkisejuhdfcvhbiuewsa.com/'}
            ],
            'status': 'Failure'
        }
        self.assertDictEqual(parse_log(self.single_target_failure, targets), expected_output)

    def test_multiple_targets_failure(self):
        targets = ["https://sfdgcxsecurityasdfawefwAed.com/", "https://afwegithubasdfasdfs.com/"]
        expected_output = {
            'links': [
                {'status': 'Failure', 'url': 'https://sfdgcxsecurityasdfawefwAed.com/'},
                {'status': 'Failure', 'url': 'https://afwegithubasdfasdfs.com/'}
            ],
            'status': 'Failure'
        }
        self.assertDictEqual(parse_log(self.multiple_targets_failure, targets), expected_output)

    def test_mixed_targets(self):
        targets = ["https://docs.xray.cool", "https://asedfawecdwsac.caedws"]
        expected_output = {
            'links': [
                {'status': 'Success', 'url': 'https://docs.xray.cool'},
                {'status': 'Failure', 'url': 'https://asedfawecdwsac.caedws'}
            ],
            'status': 'Partial Success'
        }
        self.assertDictEqual(parse_log(self.mixed_targets, targets), expected_output)