-- Cortex Analyst setup: role, user, warehouse, schema, stage, and public key.
--
-- Prerequisites:
--   * Snowflake Enterprise edition or above (Cortex Analyst requirement).
--   * SCHEMACHANGE_ROLE has CREATE ROLE / CREATE USER on the account
--     (granted in 00_bootstrap.sql).
--   * After deploying the AnalystStack, run as ACCOUNTADMIN (one-time manual step):
--       GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_ROLE;
--     (schemachange does not run as ACCOUNTADMIN so this cannot be scripted here.)
--
-- The public key below was generated from .secrets/cortex_key.pub in this repo.
-- The matching private key (.secrets/cortex_key.p8) is loaded into Secrets Manager
-- by the AnalystStack (infra/stacks/analyst_stack.py).

USE ROLE SCHEMACHANGE_ROLE;

-- --- Warehouse (XS, auto-suspend — Cortex Analyst is serverless but a warehouse
--     is required for the user session context) ---------------------------------
CREATE WAREHOUSE IF NOT EXISTS CORTEX_WH
WAREHOUSE_SIZE = 'XSMALL'
AUTO_SUSPEND = 60
AUTO_RESUME = TRUE
INITIALLY_SUSPENDED = TRUE
COMMENT = 'Used by CORTEX_USER for Cortex Analyst sessions';

-- --- Role + minimal privileges -------------------------------------------------
CREATE ROLE IF NOT EXISTS CORTEX_ROLE
COMMENT = 'Read-only access to GOLD.MARTS semantic views for Cortex Analyst';

GRANT USAGE ON WAREHOUSE CORTEX_WH TO ROLE CORTEX_ROLE;

-- Read access to the published (GOLD) semantic views/tables.
GRANT USAGE ON DATABASE GOLD TO ROLE CORTEX_ROLE;
GRANT USAGE ON SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;
GRANT SELECT ON ALL VIEWS IN SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;
GRANT SELECT ON ALL DYNAMIC TABLES IN SCHEMA GOLD.MARTS TO ROLE CORTEX_ROLE;

-- Cortex Analyst needs to read the stage that holds the semantic model file.
CREATE SCHEMA IF NOT EXISTS GOLD.CORTEX
COMMENT = 'Internal objects for Cortex Analyst (semantic model stage, etc.)';

GRANT USAGE ON SCHEMA GOLD.CORTEX TO ROLE CORTEX_ROLE;

CREATE STAGE IF NOT EXISTS GOLD.CORTEX.SEMANTIC_MODELS
    COMMENT = 'Stores Cortex Analyst semantic model YAML files';

GRANT READ ON STAGE GOLD.CORTEX.SEMANTIC_MODELS TO ROLE CORTEX_ROLE;

-- ACCOUNTADMIN must grant SNOWFLAKE.CORTEX_USER database role for API access.
-- Run the line below as ACCOUNTADMIN (outside schemachange scope):
--   GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE CORTEX_ROLE;
-- (schemachange does not run as ACCOUNTADMIN so this is left as a manual step.)

-- --- User + RSA public key registration ----------------------------------------
CREATE USER IF NOT EXISTS CORTEX_USER
    DEFAULT_ROLE = CORTEX_ROLE
    DEFAULT_WAREHOUSE = CORTEX_WH
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxURVVZ/0MiLMdgGHdDQbGJl1jf1cOFupeGsBcd2MrKT9xtd+edPOiW+rXbzJ+qixnxFp19Odv+OxEDHZl5pHe/tTUlgb0G4/9Jo44drC1sijgK/JcOG1Ui0RTPjTIaUsbbP3LEeJKhV9fnASRjQyC9XuO5ko2fWX1s9t58anyFLb8cfGpC33TmO4wzv8WbTxUyPGPMnvDTpcbT0gd/mkTfYtSepVtedd8lzc5qzhgpPjAsyYrLkKmS7SKbEUgN1Vdhh33qdlR0V5EXmUuWUBxfAAavjWrOKdrvQMhSI3ui3vI2aokyVFL0PAPS8A1JFTS3QRnlqhnCTHlqbSjKgKOQIDAQAB'  -- noqa: LT05
    COMMENT = 'Service account for the AWS Cortex Analyst Lambda';

GRANT ROLE CORTEX_ROLE TO USER CORTEX_USER;
