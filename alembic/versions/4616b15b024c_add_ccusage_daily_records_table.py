"""add ccusage_daily_records table

Revision ID: 4616b15b024c
Revises: f107f45c40c8
Create Date: 2026-02-02 15:44:58.728261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4616b15b024c'
down_revision: Union[str, None] = 'f107f45c40c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ccusage_daily_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_creation_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_read_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('models_used', postgresql.JSONB(), nullable=True),
        sa.Column('model_breakdowns', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_ccusage_date', 'ccusage_daily_records', ['date'])
    op.create_index('ix_ccusage_platform', 'ccusage_daily_records', ['platform'])

    # Create unique constraint
    op.create_unique_constraint(
        'uq_ccusage_platform_date',
        'ccusage_daily_records',
        ['platform', 'date']
    )


def downgrade() -> None:
    op.drop_constraint('uq_ccusage_platform_date', 'ccusage_daily_records', type_='unique')
    op.drop_index('ix_ccusage_platform', table_name='ccusage_daily_records')
    op.drop_index('ix_ccusage_date', table_name='ccusage_daily_records')
    op.drop_table('ccusage_daily_records')
