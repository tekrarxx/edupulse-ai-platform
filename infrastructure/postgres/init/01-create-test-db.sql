-- Runs once, only against a brand-new postgres_data volume (the official
-- Postgres image only executes /docker-entrypoint-initdb.d on first init).
-- Creates a database dedicated to the pytest suite so `make test` never
-- writes rows into the developer's own local data (§86, §105 — a test run
-- must not silently mutate state outside its own scope).
CREATE DATABASE edupulse_test;
