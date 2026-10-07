-- Run once by Postgres when its data folder is new, as the superuser: the role that owns the app's tables and
-- runs its migrations, and the database. It is not a superuser, as on a managed Postgres.
-- createrole_self_grant: the owner may switch to the roles it makes (the app's role), which rowstile's tests
-- do to look at the data as the app does.
CREATE ROLE starter_owner LOGIN PASSWORD 'owner' CREATEROLE;
ALTER ROLE starter_owner SET createrole_self_grant = 'set, inherit';
CREATE DATABASE starter OWNER starter_owner;
