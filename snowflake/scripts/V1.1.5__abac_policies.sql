-- ABAC enforcement: masking policy (column-level) + row access policy
-- (row-level), both driven by GOVERNANCE.SECURITY.ENTITLEMENTS.
USE ROLE SCHEMACHANGE_ROLE;

-- --- Column masking: hide PII unless the caller has pii_clearance ----------
CREATE MASKING POLICY IF NOT EXISTS GOVERNANCE.SECURITY.MASK_PII_STRING
AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM GOVERNANCE.SECURITY.V_ENTITLEMENTS e
            WHERE e.principal = CURRENT_ROLE()
              AND e.pii_clearance = TRUE
        )
        THEN val
        ELSE '***MASKED***'
    END;

-- --- Row access: restrict rows to the caller's entitled region -------------
CREATE ROW ACCESS POLICY IF NOT EXISTS GOVERNANCE.SECURITY.RAP_BY_REGION
AS (region VARCHAR) RETURNS BOOLEAN ->
    EXISTS (
        SELECT 1
        FROM GOVERNANCE.SECURITY.V_ENTITLEMENTS e
        WHERE e.principal = CURRENT_ROLE()
          AND (e.region = region OR e.region = 'ALL')
    );

-- --- Demo target showing both policies attached ----------------------------
-- A small, self-contained table so the demo works without dbt having run yet.
-- For real gold marts, attach the same policies via dbt post-hooks
-- (see dbt/jaffle_shop/macros/apply_governance.sql).
CREATE TABLE IF NOT EXISTS GOVERNANCE.SECURITY.CUSTOMERS_DEMO (
    customer_id NUMBER,
    full_name VARCHAR,
    email VARCHAR,
    region VARCHAR
);

INSERT INTO GOVERNANCE.SECURITY.CUSTOMERS_DEMO (customer_id, full_name, email, region)
VALUES
    (1, 'Ada Lovelace', 'ada@example.com', 'EU'),
    (2, 'Grace Hopper', 'grace@example.com', 'NA');

ALTER TABLE GOVERNANCE.SECURITY.CUSTOMERS_DEMO
    MODIFY COLUMN email SET MASKING POLICY GOVERNANCE.SECURITY.MASK_PII_STRING;
ALTER TABLE GOVERNANCE.SECURITY.CUSTOMERS_DEMO
    MODIFY COLUMN full_name SET MASKING POLICY GOVERNANCE.SECURITY.MASK_PII_STRING;

ALTER TABLE GOVERNANCE.SECURITY.CUSTOMERS_DEMO
    ADD ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_BY_REGION ON (region);
