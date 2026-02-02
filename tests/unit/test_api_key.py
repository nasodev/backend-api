# tests/unit/test_api_key.py
"""API Key 검증 단위 테스트"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.dependencies.api_key import verify_api_key


class TestVerifyApiKey:
    """API Key 검증 테스트"""

    def test_valid_api_key(self):
        """유효한 API Key 검증 성공"""
        with patch("app.dependencies.api_key.get_settings") as mock_settings:
            mock_settings.return_value.ccusage_api_key = "test-secret-key"
            result = verify_api_key("test-secret-key")
            assert result is True

    def test_invalid_api_key(self):
        """잘못된 API Key 검증 실패"""
        with patch("app.dependencies.api_key.get_settings") as mock_settings:
            mock_settings.return_value.ccusage_api_key = "test-secret-key"
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key("wrong-key")
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail

    def test_missing_api_key(self):
        """API Key 누락 시 실패"""
        with patch("app.dependencies.api_key.get_settings") as mock_settings:
            mock_settings.return_value.ccusage_api_key = "test-secret-key"
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key(None)
            assert exc_info.value.status_code == 401

    def test_empty_api_key(self):
        """빈 API Key 실패"""
        with patch("app.dependencies.api_key.get_settings") as mock_settings:
            mock_settings.return_value.ccusage_api_key = "test-secret-key"
            with pytest.raises(HTTPException) as exc_info:
                verify_api_key("")
            assert exc_info.value.status_code == 401
