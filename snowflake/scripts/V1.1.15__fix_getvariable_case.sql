-- Fix GETVARIABLE variable name casing in all masking and row access policies.
--
-- Snowflake stores SET variable names as uppercase (APP_USER_ID), but
-- GETVARIABLE receives a string literal so the case must match exactly.
-- V1.1.13 used lowercase 'app_user_id', causing all policy lookups to
-- return NULL and blocking every row regardless of the session variable value.
--
-- Uses ALTER ... SET BODY to patch each policy body in-place so that
-- attached columns/views are not disturbed.

USE ROLE SCHEMACHANGE_ROLE;

-- ── customer ───────────────────────────────────────────────────────────────

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_CUSTOMER_PII_STRING SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'customer'
            AND access_level >= 1
    ) THEN val
    ELSE '***'
END;

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_CUSTOMER_FINANCIAL_NUMBER SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'customer'
            AND access_level >= 2
    ) THEN val
END;

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_CUSTOMER SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'customer'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);

-- ── store ──────────────────────────────────────────────────────────────────

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_STORE SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'store'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);

-- ── product ────────────────────────────────────────────────────────────────

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_PRODUCT_FINANCIAL_NUMBER SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'product'
            AND access_level >= 2
    ) THEN val
END;

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_PRODUCT SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'product'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);

-- ── order ──────────────────────────────────────────────────────────────────

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_ORDER_FINANCIAL_NUMBER SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'order'
            AND access_level >= 2
    ) THEN val
END;

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_ORDER SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'order'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);

-- ── order_item ─────────────────────────────────────────────────────────────

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_ORDER_ITEM_FINANCIAL_NUMBER SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'order_item'
            AND access_level >= 2
    ) THEN val
END;

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_ORDER_ITEM SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'order_item'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);

-- ── payment ────────────────────────────────────────────────────────────────

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_PAYMENT_PII_STRING SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'payment'
            AND access_level >= 1
    ) THEN val
    ELSE '***'
END;

ALTER MASKING POLICY GOVERNANCE.SECURITY.MASK_PAYMENT_FINANCIAL_NUMBER SET BODY ->
CASE
    WHEN EXISTS (
        SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE
            user_id = GETVARIABLE('APP_USER_ID')::INTEGER
            AND resource = 'payment'
            AND access_level >= 2
    ) THEN val
END;

ALTER ROW ACCESS POLICY GOVERNANCE.SECURITY.RAP_PAYMENT SET BODY ->
GETVARIABLE('APP_USER_ID') IS NOT NULL
AND EXISTS (
    SELECT 1 FROM GOVERNANCE.SECURITY.ENTITLEMENTS
    WHERE
        user_id = GETVARIABLE('APP_USER_ID')::INTEGER
        AND resource = 'payment'
        AND access_level > 0
        AND (object_id = '*' OR object_id = object_pk::VARCHAR)
);
