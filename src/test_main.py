import pytest
import sys
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from main import main

def test_no_arguments(capsys):
    with patch.object(sys, 'argv', ['main.py']):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "Usage: ./run <install|test|url_file>" in captured.err


def test_install_dependencies_success(capsys):
    with patch.object(sys, 'argv', ['main.py', 'install']):
        with patch('subprocess.check_call', return_value=0):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0
            captured = capsys.readouterr()
            assert "All dependencies installed successfully." in captured.out

def test_install_dependencies_failure(capsys):
    with patch.object(sys, 'argv', ['main.py', 'install']):
        with patch('subprocess.check_call', side_effect=subprocess.CalledProcessError(1, 'cmd')):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1
            captured = capsys.readouterr()
            assert "Error installing dependencies" in captured.err

def test_file_not_found(capsys):
    with patch.object(sys, 'argv', ['main.py', 'non_existent_file.txt']):
        with patch('main.read_url_file', side_effect=FileNotFoundError):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1
            captured = capsys.readouterr()
            assert "Error: File not found - non_existent_file.txt" in captured.err

def test_process_url_file(capsys):
    mock_data = ["http://example.com"]
    with patch.object(sys, 'argv', ['main.py', 'url_file.txt']):
        with patch('main.read_url_file', return_value=mock_data):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0
            captured = capsys.readouterr()
            assert '{"URL": "http://example.com", "NET_SCORE": 75' in captured.out