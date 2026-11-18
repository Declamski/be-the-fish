-- Local only (docker compose): creates one database per service and one login per
-- service that can use ONLY its own database. Safe to run again (idempotent).
-- On Azure this is done once by hand during the initial setup instead.
--
-- $(DIVES_DB_PASSWORD) and $(SITES_DB_PASSWORD) are sqlcmd variables: sqlcmd fills
-- them in from environment variables of the same name (set from .env by compose).

IF DB_ID('dives') IS NULL CREATE DATABASE dives;
IF DB_ID('sites') IS NULL CREATE DATABASE sites;
GO

-- Logins (server level). If one exists, reset its password so it matches .env.
IF SUSER_ID('dives_user') IS NULL
    CREATE LOGIN dives_user WITH PASSWORD = '$(DIVES_DB_PASSWORD)';
ELSE
    ALTER LOGIN dives_user WITH PASSWORD = '$(DIVES_DB_PASSWORD)';

IF SUSER_ID('sites_user') IS NULL
    CREATE LOGIN sites_user WITH PASSWORD = '$(SITES_DB_PASSWORD)';
ELSE
    ALTER LOGIN sites_user WITH PASSWORD = '$(SITES_DB_PASSWORD)';
GO

-- dives_user gets a user in the dives database only. db_owner lets the service
-- create and alter its own tables, which the migrations need.
USE dives;
IF USER_ID('dives_user') IS NULL CREATE USER dives_user FOR LOGIN dives_user;
ALTER ROLE db_owner ADD MEMBER dives_user;
GO

-- sites_user gets a user in the sites database only.
USE sites;
IF USER_ID('sites_user') IS NULL CREATE USER sites_user FOR LOGIN sites_user;
ALTER ROLE db_owner ADD MEMBER sites_user;
GO
