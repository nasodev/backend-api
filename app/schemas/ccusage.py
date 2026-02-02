"""CCUsage API 스키마"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ModelBreakdown(BaseModel):
    """모델별 상세 사용량"""
    modelName: str
    inputTokens: int
    outputTokens: int
    cacheCreationTokens: int
    cacheReadTokens: int
    cost: float


class DailyRecord(BaseModel):
    """일별 사용량 레코드"""
    date: str  # YYYY-MM-DD
    inputTokens: int
    outputTokens: int
    cacheCreationTokens: int
    cacheReadTokens: int
    totalTokens: int
    totalCost: float
    modelsUsed: list[str]
    modelBreakdowns: list[ModelBreakdown]


class CcusageUploadRequest(BaseModel):
    """CCUsage 업로드 요청"""
    platform: str
    daily: list[DailyRecord]


class CcusageTotals(BaseModel):
    """합계"""
    inputTokens: int
    outputTokens: int
    cacheCreationTokens: int
    cacheReadTokens: int
    totalTokens: int
    totalCost: float


class CcusageDailyResponse(BaseModel):
    """일별 응답"""
    date: str
    inputTokens: int
    outputTokens: int
    cacheCreationTokens: int
    cacheReadTokens: int
    totalTokens: int
    totalCost: float
    modelsUsed: Optional[list[str]] = None
    modelBreakdowns: Optional[list[ModelBreakdown]] = None


class CcusageQueryResponse(BaseModel):
    """조회 응답"""
    platform: str  # 특정 플랫폼 or "all"
    daily: list[CcusageDailyResponse]
    totals: CcusageTotals


class CcusageUploadResponse(BaseModel):
    """업로드 응답"""
    message: str
    platform: str
    records_processed: int
