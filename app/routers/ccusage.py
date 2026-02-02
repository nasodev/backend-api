"""CCUsage 라우터"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies.api_key import verify_api_key
from app.services.ccusage.dependencies import get_ccusage_service
from app.services.ccusage.service import CcusageService
from app.schemas.ccusage import (
    CcusageUploadRequest,
    CcusageUploadResponse,
    CcusageQueryResponse,
)

router = APIRouter(prefix="/ccusage", tags=["ccusage"])


@router.post("", response_model=CcusageUploadResponse)
def upload_ccusage(
    request: CcusageUploadRequest,
    _: bool = Depends(verify_api_key),
    service: CcusageService = Depends(get_ccusage_service),
) -> CcusageUploadResponse:
    """CCUsage 데이터 업로드 (API Key 인증 필요)"""
    count = service.upsert_daily_records(request)
    return CcusageUploadResponse(
        message="Upload successful",
        platform=request.platform,
        records_processed=count,
    )


@router.get("", response_model=CcusageQueryResponse)
def query_ccusage(
    start_date: date = Query(..., description="시작일 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="종료일 (YYYY-MM-DD)"),
    platform: Optional[str] = Query(None, description="플랫폼 (생략 시 전체 합산)"),
    service: CcusageService = Depends(get_ccusage_service),
) -> CcusageQueryResponse:
    """CCUsage 사용량 조회"""
    return service.query(start_date, end_date, platform)
