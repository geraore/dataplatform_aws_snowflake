-- Medallion databases + a governance database for security objects.
USE ROLE SCHEMACHANGE_ROLE;

CREATE DATABASE IF NOT EXISTS BRONZE COMMENT = 'Raw, source-aligned data';
CREATE DATABASE IF NOT EXISTS SILVER COMMENT = 'Cleaned / conformed data';
CREATE DATABASE IF NOT EXISTS GOLD COMMENT = 'Business-ready marts';
CREATE DATABASE IF NOT EXISTS GOVERNANCE COMMENT = 'Security and access governance';

-- Default schemas used across the platform.
CREATE SCHEMA IF NOT EXISTS BRONZE.RAW COMMENT = 'Streaming + batch landing zone';
CREATE SCHEMA IF NOT EXISTS SILVER.STAGING COMMENT = 'Conformed staging models';
CREATE SCHEMA IF NOT EXISTS GOLD.MARTS COMMENT = 'Curated marts + semantic views';
