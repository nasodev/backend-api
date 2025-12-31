"""외부 연동 모듈 단위 테스트"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestFirebaseApp:
    """Firebase 앱 초기화 테스트"""

    def test_credentials_not_found(self):
        """credentials 파일이 없을 때 FileNotFoundError 발생"""
        with patch("app.external.firebase.settings") as mock_settings:
            mock_settings.firebase_credentials_path = "/nonexistent/path/credentials.json"

            # 싱글톤 초기화 상태 리셋
            import app.external.firebase as firebase_module
            original_app = firebase_module._firebase_app
            firebase_module._firebase_app = None

            try:
                with pytest.raises(FileNotFoundError) as exc_info:
                    firebase_module.get_firebase_app()

                assert "Firebase credentials not found" in str(exc_info.value)
            finally:
                # 원래 상태 복원
                firebase_module._firebase_app = original_app
