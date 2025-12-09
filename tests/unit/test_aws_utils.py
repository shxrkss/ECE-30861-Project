import pytest
from unittest.mock import patch
from src.aws_utils import upload_file_to_s3, download_file_from_s3
@pytest.fixture
def dummy_file(tmp_path):
    f = tmp_path / "dummy.txt"
    f.write_text("sample data")
    return str(f)

# Mock S3 client
@patch("src.aws_utils.s3_client")
def test_upload_file_to_s3(mock_s3, dummy_file):
    # Mock successful upload
    mock_s3.upload_file.return_value = None

    result = upload_file_to_s3(dummy_file, "models/dummy.txt")
    mock_s3.upload_file.assert_called_once()
    assert result is True

@patch("src.aws_utils.s3_client")
def test_download_file_from_s3(mock_s3, dummy_file):
    # Mock successful download
    mock_s3.download_file.return_value = None

    result = download_file_from_s3("models/dummy.txt", dummy_file)
    mock_s3.download_file.assert_called_once()
    assert result is True


@patch("src.aws_utils.s3_client")
def test_upload_failure(mock_s3, dummy_file):
    # Simulate AWS failure
    mock_s3.upload_file.side_effect = Exception("AWS upload failed")

    result = upload_file_to_s3(dummy_file, "models/fail.txt")
    assert result is False