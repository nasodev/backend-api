"""add_pending_event_table

Revision ID: f107f45c40c8
Revises: 2cc0e6c110ed
Create Date: 2026-01-22 22:27:22.950070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f107f45c40c8'
down_revision: Union[str, None] = '2cc0e6c110ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PendingEvent 테이블 생성
    op.create_table(
        'pending_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('source_image_hash', sa.String(length=64), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('confidence', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('ai_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['family_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # 인덱스 생성
    op.create_index('ix_pending_events_created_by', 'pending_events', ['created_by'], unique=False)
    op.create_index('ix_pending_events_status', 'pending_events', ['status'], unique=False)
    op.create_index('ix_pending_events_expires_at', 'pending_events', ['expires_at'], unique=False)


def downgrade() -> None:
    # 인덱스 삭제
    op.drop_index('ix_pending_events_expires_at', table_name='pending_events')
    op.drop_index('ix_pending_events_status', table_name='pending_events')
    op.drop_index('ix_pending_events_created_by', table_name='pending_events')
    # 테이블 삭제
    op.drop_table('pending_events')
