<!-- rowstile:begin -->
## Access rules (rowstile)

Who may see or change a row is decided in Postgres, by row-level security that the `rowstile` command makes
from a policy file. For coding agents working in this repository:

- The policy is `db/policy.authz`, its tests `db/tests/*.authz`; `rowstile.toml` names both.
  Everything that grants access is written in the policy: no permission checks in app code, no
  `CREATE POLICY` by hand.
- After editing it: `rowstile check` (the first mistake, with its line and a code such as `[AZ201]`), then
  `rowstile push` (the development database only) and `rowstile test`. `rowstile dev` does all three on each
  save. `rowstile help AZ201` explains a code and shows the mistake fixed.
- Production takes migrations: `rowstile migrate` writes the next one. Never `rowstile push` there.
- The app connects as `starter_app`, never as the tables' owner, and each transaction signs in first:
  `SELECT authz.act_as('user', '42')` (the SDKs do it). Then plain queries are filtered, a refused insert
  raises SQLSTATE 42501 with the reason, and an UPDATE or DELETE the rules don't allow changes no row.
- Why someone holds a permission or not: `rowstile why --as user:42 TYPE ID PERMISSION`.
- `rowstile mcp` is an MCP server with the command's tools. The language and the rest:
  https://rowstile.dev/llms.txt
<!-- rowstile:end -->

## This app

- Run the commands with `uv run` (`uv run rowstile dev`, `uv run pytest`); the README has the three
  environment variables they need.
- A new table: its model in `app/models.py`, an Alembic revision for it, then its type and its rules in
  `db/policy.authz`, then `uv run rowstile migrate` for the policy's revision.
- `app/authz_client.py`, `db/policy.lock` and `migrations/versions/*_authz_*` are written by rowstile: don't
  edit them.
