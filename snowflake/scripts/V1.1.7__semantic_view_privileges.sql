-- Grant CREATE SEMANTIC VIEW to the GOLD.READ_WRITE database role.
--
-- Snowflake treats SEMANTIC VIEW as a distinct object type from VIEW, so
-- CREATE VIEW (granted in V1.1.2) does not cover it. DBT_ROLE inherits
-- GOLD.READ_WRITE and needs this privilege to materialise the
-- Snowflake-Labs/dbt_semantic_view package output in GOLD.MARTS.
USE ROLE SCHEMACHANGE_ROLE;

GRANT CREATE SEMANTIC VIEW ON ALL SCHEMAS IN DATABASE GOLD
    TO DATABASE ROLE GOLD.READ_WRITE;

GRANT CREATE SEMANTIC VIEW ON FUTURE SCHEMAS IN DATABASE GOLD
    TO DATABASE ROLE GOLD.READ_WRITE;
