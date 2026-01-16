"""add performance indexes

Revision ID: 2cc0e6c110ed
Revises: 001
Create Date: 2026-01-16 17:55:23.732589

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2cc0e6c110ed'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 날짜 범위 쿼리 최적화를 위한 인덱스
    op.create_index('ix_events_start_time', 'events', ['start_time'])
    op.create_index('ix_events_recurrence_end', 'events', ['recurrence_end'])
    # FK 조회 최적화 (PostgreSQL은 FK에 자동 인덱스 안 만듦)
    op.create_index('ix_recurrence_exceptions_event_id', 'recurrence_exceptions', ['event_id'])


def downgrade() -> None:
    op.drop_index('ix_recurrence_exceptions_event_id', 'recurrence_exceptions')
    op.drop_index('ix_events_recurrence_end', 'events')
    op.drop_index('ix_events_start_time', 'events')
