CREATE ROLE backoffice WITH LOGIN ENCRYPTED PASSWORD 'P09olp09ol' CREATEDB;

CREATE DATABASE backoffice OWNER backoffice;
GRANT ALL PRIVILEGES ON DATABASE backoffice TO backoffice;

-- Ensure schema permissions (Required for PostgreSQL 15+)
\c backoffice
ALTER SCHEMA public OWNER TO backoffice;
GRANT ALL ON SCHEMA public TO backoffice;
