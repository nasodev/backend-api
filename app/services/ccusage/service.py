"""CCUsage 서비스"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.ccusage import CcusageDailyRecord
from app.schemas.ccusage import (
    CcusageUploadRequest,
    CcusageQueryResponse,
    CcusageDailyResponse,
    CcusageTotals,
)


class CcusageService:
    """CCUsage 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def upsert_daily_records(self, request: CcusageUploadRequest) -> int:
        """일별 레코드 upsert

        Returns:
            처리된 레코드 수
        """
        count = 0
        for record in request.daily:
            record_date = datetime.strptime(record.date, "%Y-%m-%d").date()

            stmt = insert(CcusageDailyRecord).values(
                platform=request.platform,
                date=record_date,
                input_tokens=record.inputTokens,
                output_tokens=record.outputTokens,
                cache_creation_tokens=record.cacheCreationTokens,
                cache_read_tokens=record.cacheReadTokens,
                total_tokens=record.totalTokens,
                total_cost=record.totalCost,
                models_used=record.modelsUsed,
                model_breakdowns=[mb.model_dump() for mb in record.modelBreakdowns],
            )

            stmt = stmt.on_conflict_do_update(
                constraint="uq_ccusage_platform_date",
                set_={
                    "input_tokens": stmt.excluded.input_tokens,
                    "output_tokens": stmt.excluded.output_tokens,
                    "cache_creation_tokens": stmt.excluded.cache_creation_tokens,
                    "cache_read_tokens": stmt.excluded.cache_read_tokens,
                    "total_tokens": stmt.excluded.total_tokens,
                    "total_cost": stmt.excluded.total_cost,
                    "models_used": stmt.excluded.models_used,
                    "model_breakdowns": stmt.excluded.model_breakdowns,
                    "updated_at": datetime.utcnow(),
                },
            )

            self.db.execute(stmt)
            count += 1

        self.db.commit()
        return count

    def query(
        self,
        start_date: date,
        end_date: date,
        platform: Optional[str] = None,
    ) -> CcusageQueryResponse:
        """사용량 조회

        Args:
            start_date: 시작일
            end_date: 종료일
            platform: 플랫폼 (None이면 전체 합산)

        Returns:
            조회 결과
        """
        query = self.db.query(CcusageDailyRecord).filter(
            CcusageDailyRecord.date >= start_date,
            CcusageDailyRecord.date <= end_date,
        )

        if platform:
            query = query.filter(CcusageDailyRecord.platform == platform)

        records = query.order_by(CcusageDailyRecord.date).all()

        if platform:
            # 특정 플랫폼: 그대로 반환
            daily = [
                CcusageDailyResponse(
                    date=r.date.isoformat(),
                    inputTokens=r.input_tokens,
                    outputTokens=r.output_tokens,
                    cacheCreationTokens=r.cache_creation_tokens,
                    cacheReadTokens=r.cache_read_tokens,
                    totalTokens=r.total_tokens,
                    totalCost=r.total_cost,
                    modelsUsed=r.models_used,
                    modelBreakdowns=r.model_breakdowns,
                )
                for r in records
            ]
        else:
            # 전체: 날짜별 합산
            date_aggregates: dict[date, dict] = {}
            for r in records:
                if r.date not in date_aggregates:
                    date_aggregates[r.date] = {
                        "inputTokens": 0,
                        "outputTokens": 0,
                        "cacheCreationTokens": 0,
                        "cacheReadTokens": 0,
                        "totalTokens": 0,
                        "totalCost": 0.0,
                    }
                agg = date_aggregates[r.date]
                agg["inputTokens"] += r.input_tokens
                agg["outputTokens"] += r.output_tokens
                agg["cacheCreationTokens"] += r.cache_creation_tokens
                agg["cacheReadTokens"] += r.cache_read_tokens
                agg["totalTokens"] += r.total_tokens
                agg["totalCost"] += r.total_cost

            daily = [
                CcusageDailyResponse(
                    date=d.isoformat(),
                    **agg,
                )
                for d, agg in sorted(date_aggregates.items())
            ]

        # 합계 계산
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
