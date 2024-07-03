import os
import unittest
from unittest.mock import patch, MagicMock
import subprocess
import requests
from api.utils import check_docker_version, check_docker_compose, initialize_archivebox


class TestUtils(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()
