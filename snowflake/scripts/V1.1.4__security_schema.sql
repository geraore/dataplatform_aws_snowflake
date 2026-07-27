-- Security schema + ABAC entitlements table.
--
-- The entitlements table is the single source of truth for attribute-based
-- access control (ABAC). Masking and row-access policies (V1.1.5) read it to
-- decide what each caller may see.
USE ROLE SCHEMACHANGE_ROLE;

CREATE SCHEMA IF NOT EXISTS GOVERNANCE.SECURITY COMMENT = 'ABAC policies + entitlements';

CREATE TABLE IF NOT EXISTS GOVERNANCE.SECURITY.ENTITLEMENTS (
    -- The Snowflake principal the entitlement applies to (a role name).
    principal VARCHAR NOT NULL,
    -- Attributes that drive access decisions.
    region VARCHAR,                       -- row-level filter, e.g. 'EU', 'NA'
    department VARCHAR,                    -- row-level filter
    pii_clearance BOOLEAN DEFAULT FALSE,   -- column-level: may see unmasked PII
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_entitlements PRIMARY KEY (principal, region, department)
);

-- Sample entitlements for the demo.
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS
(principal, region, department, pii_clearance)
VALUES
('ANALYST_EU', 'EU', 'SALES', FALSE),
('ANALYST_NA', 'NA', 'SALES', FALSE),
('DATA_STEWARD', 'ALL', 'ALL', TRUE);

-- Helper view: flatten "ALL" wildcards for easy policy joins.
CREATE OR REPLACE VIEW GOVERNANCE.SECURITY.V_ENTITLEMENTS AS
SELECT
    principal,
    region,
    department,
    pii_clearance
FROM GOVERNANCE.SECURITY.ENTITLEMENTS
WHERE is_active = TRUE;
