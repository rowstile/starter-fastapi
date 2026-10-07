# rowstile starter: FastAPI

Documents that people share with each other and with teams, in a FastAPI app with SQLAlchemy and Alembic.
There is no permission check in the app's code. Who may see and change a document is written in one file,
[`db/policy.authz`](db/policy.authz), which [rowstile](https://rowstile.dev) compiles into Postgres row-level
security: the database filters every read and refuses every write the rules don't allow.

## Run it

    docker compose up --build

That starts Postgres, runs the migrations (the tables, then the policy) and serves the API on
<http://localhost:8000> (try it at <http://localhost:8000/docs>). Three people are there: ann (1), bo (2) and
cy (3), and cy is in the team "writers" (10). A request says who it is with the header `x-user`.

    U=http://localhost:8000; J='content-type: application/json'
    curl -X POST $U/documents -H 'x-user: 1' -H "$J" -d '{"title": "Plan"}'     # ann makes a document: {"id":1}
    curl $U/documents -H 'x-user: 2'                                          # bo sees nothing: []
    curl -X POST $U/documents/1/shares -H 'x-user: 1' -H "$J" -d '{"relation": "viewer", "user_id": 2}'
    curl $U/documents -H 'x-user: 2'                                          # now he does, and may only view
    curl -X PATCH $U/documents/1 -H 'x-user: 2' -H "$J" -d '{"title": "mine"}'  # 403, with the rule and why
    curl -X POST $U/documents/1/shares -H 'x-user: 1' -H "$J" -d '{"relation": "editor", "team_id": 10}'
    curl -X PATCH $U/documents/1 -H 'x-user: 3' -H "$J" -d '{"body": "by cy"}'  # cy, of the writers, edits
    curl $U/documents/1/access -H 'x-user: 1'                                 # who can view, who can edit

## What is where

| | |
|---|---|
| [`db/policy.authz`](db/policy.authz) | the rules: who owns, who may share, what a viewer and an editor may do |
| [`db/tests/sharing.authz`](db/tests/sharing.authz) | the rules' tests: each brings its own rows and is rolled back |
| [`app/main.py`](app/main.py) | the routes, with no checks in them |
| [`app/models.py`](app/models.py), [`migrations/`](migrations/) | the tables, and Alembic's revisions; the policy is one of them |
| [`rowstile.toml`](rowstile.toml) | where the policy, its tests and its migrations are |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | the tests, and on a pull request a comment that says who gains or loses access |

Two roles connect to the database. `starter_owner` owns the tables and runs the migrations. The app connects
as `starter_app`, which row-level security applies to. Never give the app the owner's connection: row-level
security doesn't apply to a table's owner.

## Change the rules

You need Python 3.11 or later and [uv](https://docs.astral.sh/uv/). With the containers up:

    uv sync
    export ROWSTILE_OWNER_DSN=postgresql://starter_owner:owner@localhost:15432/starter
    export ROWSTILE_OWNER_URL=postgresql+psycopg://starter_owner:owner@localhost:15432/starter
    export ROWSTILE_APP_URL=postgresql+asyncpg://starter_app:app@localhost:15432/starter
    uv run rowstile push --development # once: migrations set this database up, so say it is a development one
    uv run rowstile dev                # on every save: check, apply to this database, run the tests

Edit `db/policy.authz` (say, let an editor share: `can share = owner or editor`) and watch `rowstile dev` say who
gains access and which tests now fail. When the change is what you want:

    uv run rowstile migrate            # writes the next Alembic revision, from db/policy.lock
    uv run pytest                      # the app's own tests

`rowstile dev` changes this database directly, which is fine for a database on your laptop. Any other database
takes migrations only: `uv run alembic upgrade head`. To start over, `docker compose down -v`.

## Make it yours

- **Who the request is.** `user_of` in `app/main.py` believes a header. Replace it with your session or your
  token before anyone else can reach the app.
- **The passwords** in `docker-compose.yml` and `docker/init.sql` are for a laptop.
- **The people and the team** are made by the first migration, for the walk above. Delete those lines.
- **Your tables.** Add them to `app/models.py`, write their Alembic revision, then give them a type and rules in
  the policy. A table without rules is readable by the app in full; `uv run rowstile lint` lists them.

rowstile is a 0.x preview: its language and its functions may still change before 1.0, and nobody outside
the project has audited it ([how it is checked](https://rowstile.dev/how-it-is-checked)). The docs:
[FastAPI, SQLAlchemy and Alembic](https://rowstile.dev/stacks/fastapi), [the policy language](https://rowstile.dev/reference/language),
[the cookbook](https://rowstile.dev/cookbook/).

This starter is yours to take and change: [Apache-2.0](LICENSE).
