#!/bin/sh
# Runs only for a new PostgreSQL volume. Existing data is never reset here.
set -eu
: "${POSTGRES_USER:?required}" "${DB_OWNER_PASSWORD:?required}" "${DB_APP_PASSWORD:?required}" "${DB_TEST_PASSWORD:?required}"

# psql SQL-literal quoting, not shell substitution into SQL.
psql --username "$POSTGRES_USER" --dbname postgres --set ON_ERROR_STOP=1 \
  --set owner_password="$DB_OWNER_PASSWORD" \
  --set app_password="$DB_APP_PASSWORD" \
  --set test_password="$DB_TEST_PASSWORD" <<'SQL'
CREATE ROLE app_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'owner_password';
CREATE ROLE app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'app_password';
CREATE ROLE test_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'test_password';
CREATE DATABASE elseview_app OWNER app_owner;
CREATE DATABASE elseview_test OWNER test_owner;
REVOKE ALL ON DATABASE elseview_app FROM PUBLIC;
REVOKE ALL ON DATABASE elseview_test FROM PUBLIC;
GRANT CONNECT ON DATABASE elseview_app TO app;
\connect elseview_app
ALTER SCHEMA public OWNER TO app_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO app;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
\connect elseview_test
ALTER SCHEMA public OWNER TO test_owner;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL