"""CCUsage 엔드포인트 통합 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ccusage.dependencies import get_ccusage_service
from app.dependencies.api_key import verify_api_key
from tests.fakes import FakeCcusageService


@pytest.fixture
def fake_ccusage_service():
    """Fake CCUsage 서비스"""
    return FakeCcusageService()


@pytest.fixture
def client_with_fake_ccusage(fake_ccusage_service):
    """CCUsage 서비스가 Fake로 대체된 테스트 클라이언트"""
    app.dependency_overrides[get_ccusage_service] = lambda: fake_ccusage_service
    app.dependency_overrides[verify_api_key] = lambda: True
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestCcusageUpload:
    """CCUsage 업로드 테스트"""

    def test_upload_success(self, client_with_fake_ccusage):
        """업로드 성공"""
        payload = {
            "platform": "mac-com",
            "daily": [
                {
                    "date": "2026-01-01",
                    "inputTokens": 1000,
                    "outputTokens": 500,
                    "cacheCreationTokens": 2000,
                    "cacheReadTokens": 3000,
                    "totalTokens": 6500,
                    "totalCost": 0.50,
                    "modelsUsed": ["claude-opus-4-5-20251101"],
                    "modelBreakdowns": [
                        {
                            "modelName": "claude-opus-4-5-20251101",
                            "inputTokens": 1000,
                            "outputTokens": 500,
                            "cacheCreationTokens": 2000,
                            "cacheReadTokens": 3000,
                            "cost": 0.50,
                        }
                    ],
                }
            ],
        }

        response = client_with_fake_ccusage.post(
            "/ccusage",
            json=payload,
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "mac-com"
        assert data["records_processed"] == 1

    def test_upload_without_api_key(self, client):
        """API Key 없이 업로드 시 401"""
        payload = {"platform": "mac-com", "daily": []}

        response = client.post("/ccusage", json=payload)

        assert response.status_code == 401


class TestCcusageQuery:
    """CCUsage 조회 테스트"""

    def test_query_by_platform(self, client_with_fake_ccusage, fake_ccusage_service):
        """플랫폼별 조회"""
        from app.schemas.ccusage import CcusageUploadRequest, DailyRecord, ModelBreakdown

        fake_ccusage_service.upsert_daily_records(
            CcusageUploadRequest(
                platform="mac-com",
                daily=[
                    DailyRecord(
                        date="2026-01-01",
                        inputTokens=1000,
                        outputTokens=500,
                        cacheCreationTokens=2000,
                        cacheReadTokens=3000,
                        totalTokens=6500,
                        totalCost=0.50,
                        modelsUsed=["claude-opus-4-5-20251101"],
                        modelBreakdowns=[
                            ModelBreakdown(
                                modelName="claude-opus-4-5-20251101",
                                inputTokens=1000,
                                outputTokens=500,
                                cacheCreationTokens=2000,
                                cacheReadTokens=3000,
                                cost=0.50,
                            )
                        ],
                    )
                ],
            )
        )

        response = client_with_fake_ccusage.get(
            "/ccusage",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "platform": "mac-com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "mac-com"
        assert len(data["daily"]) == 1
        assert data["totals"]["inputTokens"] == 1000

    def test_query_all_platforms(self, client_with_fake_ccusage, fake_ccusage_service):
        """전체 플랫폼 합산 조회"""
        from app.schemas.ccusage import CcusageUploadRequest, DailyRecord, ModelBreakdown

        for platform in ["mac-com", "window-com"]:
            fake_ccusage_service.upsert_daily_records(
                CcusageUploadRequest(
                    platform=platform,
                    daily=[
                        DailyRecord(
                            date="2026-01-01",
                            inputTokens=1000,
                            outputTokens=500,
                            cacheCreationTokens=2000,
                            cacheReadTokens=3000,
                            totalTokens=6500,
                            totalCost=0.50,
                            modelsUsed=["claude-opus-4-5-20251101"],
                            modelBreakdowns=[
                                ModelBreakdown(
                                    modelName="claude-opus-4-5-20251101",
                                    inputTokens=1000,
                                    outputTokens=500,
                                    cacheCreationTokens=2000,
                                    cacheReadTokens=3000,
                                    cost=0.50,
                                )
                            ],
                        )
                    ],
                )
            )

        response = client_with_fake_ccusage.get(
            "/ccusage",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "all"
        assert data["totals"]["inputTokens"] == 2000

    def test_query_missing_dates(self, client_with_fake_ccusage):
        """날짜 파라미터 누락 시 422"""
        response = client_with_fake_ccusage.get("/ccusage")
        assert response.status_code == 422
