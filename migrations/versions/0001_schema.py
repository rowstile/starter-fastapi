"""the app's tables, the role it connects as, and a few people to try it with

Revision ID: 0001
Revises:
"""

import os

from alembic import op
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA app")
    Base.metadata.create_all(bind=op.get_bind())
    # The role the app connects as. Row-level security applies to it: it is not a superuser, does not bypass
    # row-level security, and owns no table. The owner (who runs this) makes it and may switch to it, which
    # rowstile's tests need.
    password = os.environ.get("STARTER_APP_PASSWORD", "app").replace("'", "''")
    op.execute(f"""DO $$ BEGIN
      IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'starter_app') THEN
        CREATE ROLE starter_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
      END IF; END $$""")
    op.execute("ALTER ROLE starter_app SET jit = off")
    op.execute("GRANT USAGE ON SCHEMA app TO starter_app")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA app TO starter_app")
    op.execute("GRANT INSERT, UPDATE, DELETE ON app.documents TO starter_app")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO starter_app")
    # people and a team to try it with (the README's walk uses them): delete these lines in your app
    op.execute("INSERT INTO app.users VALUES (1, 'ann'), (2, 'bo'), (3, 'cy')")
    op.execute("INSERT INTO app.teams VALUES (10, 'writers')")
    op.execute("INSERT INTO app.team_members VALUES (10, 3)")


def downgrade() -> None:
    op.execute("DROP SCHEMA app CASCADE")
