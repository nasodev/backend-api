"""CCUsage 사용량 데이터 모델"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.external.database import Base


class CcusageDailyRecord(Base):
    """일별 CCUsage 사용량 기록"""
    __tablename__ = "ccusage_daily_records"
    __table_args__ = (
        UniqueConstraint("platform", "date", name="uq_ccusage_platform_date"),
        Index("ix_ccusage_date", "date"),
        Index("ix_ccusage_platform", "platform"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    models_used: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    model_breakdowns: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
