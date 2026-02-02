"""Fake CCUsage 서비스"""

from datetime import date
from typing import Optional

from app.schemas.ccusage import (
    CcusageUploadRequest,
    CcusageQueryResponse,
    CcusageDailyResponse,
    CcusageTotals,
)


class FakeCcusageService:
    """Fake CCUsage 서비스"""

    def __init__(self):
        self.records: list[dict] = []

    def upsert_daily_records(self, request: CcusageUploadRequest) -> int:
        """일별 레코드 upsert"""
        count = 0
        for record in request.daily:
            # 기존 레코드 찾기
            existing = None
            for r in self.records:
                if r["platform"] == request.platform and r["date"] == record.date:
                    existing = r
                    break

            if existing:
                existing.update({
                    "inputTokens": record.inputTokens,
                    "outputTokens": record.outputTokens,
                    "cacheCreationTokens": record.cacheCreationTokens,
                    "cacheReadTokens": record.cacheReadTokens,
                    "totalTokens": record.totalTokens,
                    "totalCost": record.totalCost,
                    "modelsUsed": record.modelsUsed,
                    "modelBreakdowns": [mb.model_dump() for mb in record.modelBreakdowns],
                })
            else:
                self.records.append({
                    "platform": request.platform,
                    "date": record.date,
                    "inputTokens": record.inputTokens,
                    "outputTokens": record.outputTokens,
                    "cacheCreationTokens": record.cacheCreationTokens,
                    "cacheReadTokens": record.cacheReadTokens,
                    "totalTokens": record.totalTokens,
                    "totalCost": record.totalCost,
                    "modelsUsed": record.modelsUsed,
                    "modelBreakdowns": [mb.model_dump() for mb in record.modelBreakdowns],
                })
            count += 1
        return count

    def query(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
    ) -> CcusageQueryResponse:
        """사용량 조회"""
        filtered = [
            r for r in self.records
            if start_date.isoformat() <= r["date"] <= end_date.isoformat()
            and (platform is None or r["platform"] == platform)
        ]

        if platform:
            daily = [
                CcusageDailyResponse(
                    date=r["date"],
                    inputTokens=r["inputTokens"],
                    outputTokens=r["outputTokens"],
                    cacheCreationTokens=r["cacheCreationTokens"],
                    cacheReadTokens=r["cacheReadTokens"],
                    totalTokens=r["totalTokens"],
                    totalCost=r["totalCost"],
                    modelsUsed=r["modelsUsed"],
                    modelBreakdowns=r["modelBreakdowns"],
                )
                for r in sorted(filtered, key=lambda x: x["date"])
            ]
        else:
            date_aggregates: dict[str, dict] = {}
            for r in filtered:
                if r["date"] not in date_aggregates:
                    date_aggregates[r["date"]] = {
                        "inputTokens": 0,
                        "outputTokens": 0,
                        "cacheCreationTokens": 0,
                        "cacheReadTokens": 0,
                        "totalTokens": 0,
                        "totalCost": 0.0,
                    }
                agg = date_aggregates[r["date"]]
                agg["inputTokens"] += r["inputTokens"]
                agg["outputTokens"] += r["outputTokens"]
                agg["cacheCreationTokens"] += r["cacheCreationTokens"]
                agg["cacheReadTokens"] += r["cacheReadTokens"]
                agg["totalTokens"] += r["totalTokens"]
                agg["totalCost"] += r["totalCost"]

            daily = [
                CcusageDailyResponse(date=d, **agg)
                for d, agg in sorted(date_aggregates.items())
            ]

        totals = CcusageTotals(
            inputTokens=sum(d.inputTokens for d in daily),
            outputTokens=sum(d.outputTokens for d in daily),
            cacheCreationTokens=sum(d.cacheCreationTokens for d in daily),
            cacheReadTokens=sum(d.cacheReadTokens for d in daily),
            totalTokens=sum(d.totalTokens for d in daily),
            totalCost=sum(d.totalCost for d in daily),
        )

        return CcusageQueryResponse(
            platform=platform or "all",
            daily=daily,
            totals=totals,
        )
