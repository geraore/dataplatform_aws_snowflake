-- Per-resource masking and row-access policies aligned with the V1.1.12
-- entitlements schema (user_id, resource, access_level, object_id).
--
-- dbt (DBT_ROLE) only references these policies; it does not create them.
-- Policy naming mirrors what apply_column_masking and the secured view
-- schema.yml row_access_policy configs expect:
--
--   MASK_<RESOURCE>_PII_STRING       VARCHAR columns (access_level >= 1)
--   MASK_<RESOURCE>_FINANCIAL_NUMBER NUMBER  columns (access_level >= 2)
--   RAP_<RESOURCE>                   row-level guard  (access_level > 0)
--
-- Resources: customer, store, product, order, order_item, payment.
-- store has no sensitive columns so it gets only a RAP.
USE ROLE SCHEMACHANGE_ROLE;

-- ── customer ───────────────────────────────────────────────────────────────

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_CUSTOMER_PII_STRING
AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'customer'
              AND  access_level >= 1
        ) THEN val
        ELSE '***'
    END;

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_CUSTOMER_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'customer'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_CUSTOMER
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'customer'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );

-- ── store (row-level only; no sensitive columns) ──────────────────────────

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_STORE
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'store'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );

-- ── product ────────────────────────────────────────────────────────────────

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_PRODUCT_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'product'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_PRODUCT
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'product'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );

-- ── order ──────────────────────────────────────────────────────────────────

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_ORDER_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'order'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_ORDER
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'order'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );

-- ── order_item ─────────────────────────────────────────────────────────────

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_ORDER_ITEM_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'order_item'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_ORDER_ITEM
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'order_item'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );

-- ── payment ────────────────────────────────────────────────────────────────

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_PAYMENT_PII_STRING
AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'payment'
              AND  access_level >= 1
        ) THEN val
        ELSE '***'
    END;

CREATE OR REPLACE MASKING POLICY GOVERNANCE.SECURITY.MASK_PAYMENT_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = 'payment'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;

CREATE OR REPLACE ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_PAYMENT
AS (object_pk INTEGER) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = 'payment'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );
