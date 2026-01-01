"""add calendar tables

Revision ID: 001
Revises:
Create Date: 2026-01-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create family_members table
    op.create_table(
        'family_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('firebase_uid', sa.String(128), unique=True, nullable=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(7), nullable=False),
        sa.Column('is_registered', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('color', sa.String(7), nullable=False),
        sa.Column('icon', sa.String(50), nullable=True),
    )

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('all_day', sa.Boolean(), default=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('family_members.id'), nullable=False),
        sa.Column('recurrence_rule', sa.String(500), nullable=True),
        sa.Column('recurrence_start', sa.Date(), nullable=True),
        sa.Column('recurrence_end', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create recurrence_exceptions table
    op.create_table(
        'recurrence_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('original_date', sa.Date(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('modified_event', postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('recurrence_exceptions')
    op.drop_table('events')
    op.drop_table('categories')
    op.drop_table('family_members')
