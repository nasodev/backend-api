"""Run the additive migration against a disposable database, then reverse it."""
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def test_migration_creates_comment_tables_indexes_and_self_reference():
    path = Path(__file__).resolve().parents[3] / 'alembic/versions/a381e14d3e7f_add_blog_comments.py'
    spec = importlib.util.spec_from_file_location('comment_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine('sqlite://')
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        schema = inspect(connection)
        assert set(schema.get_table_names()) == {'blog_comments', 'blog_comment_password_attempts'}
        assert {tuple(index['column_names']) for index in schema.get_indexes('blog_comments')} == {
            ('thread_slug', 'created_at', 'id'), ('parent_id',), ('author_uid', 'created_at'), ('creation_rate_key', 'created_at'),
        }
        foreign_keys = schema.get_foreign_keys('blog_comments')
        assert len(foreign_keys) == 1
        assert foreign_keys[0]['referred_table'] == 'blog_comments'
        assert schema.get_unique_constraints('blog_comments')[0]['column_names'] == ['external_id']
        module.downgrade()
        assert inspect(connection).get_table_names() == []
    engine.dispose()
