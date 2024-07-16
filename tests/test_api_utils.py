import os
import unittest

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'archivebox_api_server.settings')
django.setup()

from api.utils import parse_log


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

        self.already_exists_targets = """
[+] [2024-07-16 08:56:13] Adding 2 links to index (crawl depth=0)...
    > Saved verbatim input to sources/1721120173-import.txt
    > Parsed 2 URLs from input (Generic TXT)
    > Found 0 new URLs not already in index

[*] [2024-07-16 08:56:13] Writing 0 links to main index...

    √ ./index.sqlite3
    """

    def test_single_target_success(self):
        targets = ["https://www.baidu.com/"]
        expected_output = [{'url': 'https://www.baidu.com/', 'archive_path': './archive/1720073769.137125'}]
        result = parse_log(self.single_target_success, targets)
        self.assertListEqual(result['data'], expected_output)

    def test_multiple_targets_success(self):
        targets = ["https://cxsecurity.com/cveshow/CVE-2022-34593/", "https://github.com/Liyou-ZY/POC/issues/1"]
        expected_output = [
            {'url': 'https://cxsecurity.com/cveshow/CVE-2022-34593/', 'archive_path': './archive/1720074402.409496'},
            {'url': 'https://github.com/Liyou-ZY/POC/issues/1', 'archive_path': './archive/1720074402.409769'}
        ]
        result = parse_log(self.multiple_targets_success, targets)
        self.assertListEqual(result['data'], expected_output)

    def test_mixed_targets(self):
        targets = ["https://docs.xray.cool", "https://asedfawecdwsac.caedws"]
        expected_output = [
            {'url': 'https://docs.xray.cool', 'archive_path': './archive/1720075521.41685'},
            {'url': 'https://asedfawecdwsac.caedws', 'archive_path': './archive/1720075521.417146'}
        ]
        self.assertListEqual(parse_log(self.mixed_targets, targets)['data'], expected_output)

    def test_already_exists_success(self):
        targets = ["https://docs.xray.cool", "https://asedfawecdwsac.caedws"]
        self.assertEqual(parse_log(self.already_exists_targets, targets)['message'],
                         "The requested target already exists. If you want to update it, please add the update parameter.")
