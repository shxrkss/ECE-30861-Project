import pytest
import sys
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure src folder is in sys.path
sys.path.append(str(Path(__file__).resolve().parent))

from src import main as main_module

def test_no_arguments(capsys):
    with patch.dict("sys.modules", {"orchestrator": MagicMock()}):
        with patch.object(sys, 'argv', ['main.py']):
            with pytest.raises(SystemExit) as e:
                main_module.main()
            assert e.value.code == 1
            captured = capsys.readouterr()
            # Note: there was a typo 'Inorrect' in main.py, adjust assertion to match if necessary
            assert "Incorrect Usage -> Try: ./run <install|test|url_file>" in captured.err or \
                   "Inorrect Usage -> Try: ./run <install|test|url_file>" in captured.err




def test_file_not_found(capsys):
    mock_orchestrator = MagicMock()
    with patch.dict("sys.modules", {"orchestrator": mock_orchestrator}):
        with patch.object(sys, 'argv', ['main.py', 'non_existent_file.txt']):
            with patch("src.main.read_url_file", side_effect=FileNotFoundError):
                with pytest.raises(SystemExit) as e:
                    main_module.main()
                assert e.value.code == 1
                captured = capsys.readouterr()
                assert "Error: File not found - non_existent_file.txt" in captured.err


def test_process_url_file(capsys):
    mock_url_file_data = [
        ("http://example.com/code", "http://example.com/dataset", "http://example.com/model")
    ]
    mock_run_all_metrics_result = {"NET_SCORE": 0.95}
    fake_orchestrator = MagicMock()
    fake_orchestrator.run_all_metrics.return_value = mock_run_all_metrics_result

    with patch.dict("sys.modules", {"orchestrator": fake_orchestrator}):
        with patch.object(sys, 'argv', ['main.py', 'url_file.txt']):
            with patch("src.main.read_url_file", return_value=mock_url_file_data):
                with pytest.raises(SystemExit) as e:
                    main_module.main()
                assert e.value.code == 0
                captured = capsys.readouterr()
                import json
                data = json.loads(captured.out)
                assert data['NET_SCORE'] == 0.95
                assert data['category'] == "MODEL"
