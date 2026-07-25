"""add blog_posts table

Revision ID: 707aae763c56
Revises: 4616b15b024c
Create Date: 2026-07-25 13:29:22.089844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '707aae763c56'
down_revision: Union[str, None] = '4616b15b024c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(200), unique=True, nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('author', sa.String(100), nullable=False, server_default='fundev'),
        sa.Column('content_html', sa.Text(), nullable=False),
        sa.Column('cover_image_url', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('toc', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('reading_time_minutes', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create index
    op.create_index('ix_blog_posts_published_at', 'blog_posts', ['published_at'])


def downgrade() -> None:
    op.drop_index('ix_blog_posts_published_at', table_name='blog_posts')
    op.drop_table('blog_posts')
