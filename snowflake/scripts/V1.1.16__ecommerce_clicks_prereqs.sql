-- Prerequisites for the ecommerce_clicks dbt dynamic table.
--
-- CHANGE_TRACKING lets Snowflake use incremental refresh mode on the dynamic
-- table (AUTO lets the engine decide; incremental is preferred when upstream
-- data changes are append-only, as is the case for BRONZE.RAW.EVENTS).
--
-- CREATE DYNAMIC TABLE is a separate privilege from CREATE TABLE in Snowflake;
-- DBT_ROLE gets it through the SILVER.READ_WRITE database role.
USE ROLE SCHEMACHANGE_ROLE;

ALTER TABLE BRONZE.RAW.EVENTS SET CHANGE_TRACKING = TRUE;

GRANT CREATE DYNAMIC TABLE ON SCHEMA SILVER.STAGING
TO DATABASE ROLE SILVER.READ_WRITE;
