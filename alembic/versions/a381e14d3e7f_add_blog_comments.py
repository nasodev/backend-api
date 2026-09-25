"""Add native blog comments and durable guest verification attempts.

Revision ID: a381e14d3e7f
Revises: 707aae763c56
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a381e14d3e7f'
down_revision = '707aae763c56'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'blog_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('thread_slug', sa.String(200), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('blog_comments.id'), nullable=True),
        sa.Column('author_type', sa.String(10), nullable=False),
        sa.Column('author_uid', sa.String(128), nullable=True),
        sa.Column('password_hash', sa.String(256), nullable=True),
        sa.Column('creation_rate_key', sa.String(64), nullable=True),
        sa.Column('author_name', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_id', sa.String(200), unique=True, nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.CheckConstraint("author_type IN ('google', 'guest', 'github')", name='ck_blog_comments_author_type'),
    )
    op.create_index('ix_blog_comments_thread_created_id', 'blog_comments', ['thread_slug', 'created_at', 'id'])
    op.create_index('ix_blog_comments_parent', 'blog_comments', ['parent_id'])
    op.create_index('ix_blog_comments_author_created', 'blog_comments', ['author_uid', 'created_at'])
    op.create_index('ix_blog_comments_rate_created', 'blog_comments', ['creation_rate_key', 'created_at'])
    op.create_table(
        'blog_comment_password_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_key', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_blog_comment_attempt_actor_created', 'blog_comment_password_attempts', ['actor_key', 'created_at'])


def downgrade():
    op.drop_table('blog_comment_password_attempts')
    op.drop_table('blog_comments')
