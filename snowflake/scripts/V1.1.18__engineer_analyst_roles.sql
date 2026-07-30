-- Human operator roles and RBAC masking policies.
--
-- DATA_ENGINEER_ROLE: read access across all four databases (BRONZE, SILVER,
--   GOLD, GOVERNANCE) — full pipeline visibility, no column masking.
--
-- ANALYST_NO_PII: read-only access to GOLD marts. PII columns (first_name,
--   last_name, …) are masked at query time by the masking policies below.
--
-- Masking convention: any role whose name contains NO_PII sees masked values.
-- CURRENT_ROLE() LIKE '%NO_PII%' is evaluated at query time against the
-- session's primary role — no database-context dependency. Adding a new
-- restricted role requires only the naming convention; no policy change needed.
USE ROLE SCHEMACHANGE_ROLE;

-- ========================= DATA_ENGINEER_ROLE ================================
CREATE ROLE IF NOT EXISTS DATA_ENGINEER_ROLE
COMMENT = 'Read access across all databases for data engineers';

GRANT DATABASE ROLE BRONZE.READ_ONLY TO ROLE DATA_ENGINEER_ROLE;
GRANT DATABASE ROLE SILVER.READ_ONLY TO ROLE DATA_ENGINEER_ROLE;
GRANT DATABASE ROLE GOLD.READ_ONLY TO ROLE DATA_ENGINEER_ROLE;
GRANT DATABASE ROLE GOVERNANCE.READ_ONLY TO ROLE DATA_ENGINEER_ROLE;

GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATA_ENGINEER_ROLE;
GRANT ROLE DATA_ENGINEER_ROLE TO ROLE SYSADMIN;

-- ========================= ANALYST_NO_PII ====================================
CREATE ROLE IF NOT EXISTS ANALYST_NO_PII
COMMENT = 'Read-only access to GOLD marts; PII masked by role name convention';

GRANT DATABASE ROLE GOLD.READ_ONLY TO ROLE ANALYST_NO_PII;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE ANALYST_NO_PII;
GRANT ROLE ANALYST_NO_PII TO ROLE SYSADMIN;

-- ========================= RBAC MASKING POLICIES ============================
CREATE MASKING POLICY IF NOT EXISTS GOVERNANCE.SECURITY.MASK_NO_PII_STRING
AS(val VARCHAR) RETURNS VARCHAR ->
CASE
    WHEN CURRENT_ROLE() LIKE '%NO_PII%' THEN '***'
    ELSE val
END;

CREATE MASKING POLICY IF NOT EXISTS GOVERNANCE.SECURITY.MASK_NO_PII_NUMBER
AS(val NUMBER) RETURNS NUMBER ->
CASE
    WHEN CURRENT_ROLE() LIKE '%NO_PII%' THEN NULL
    ELSE val
END;

-- DBT_ROLE needs APPLY privilege to attach these policies via post-hooks.
GRANT APPLY ON MASKING POLICY GOVERNANCE.SECURITY.MASK_NO_PII_STRING TO ROLE DBT_ROLE;
GRANT APPLY ON MASKING POLICY GOVERNANCE.SECURITY.MASK_NO_PII_NUMBER TO ROLE DBT_ROLE;
