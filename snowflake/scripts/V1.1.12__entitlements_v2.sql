-- Resource-level entitlements table (replaces the ABAC table from V1.1.4).
--
-- access_level:
--   0 = no access (same as no row)
--   1 = read with PII visible
--   2 = read all (full access, including all columns and metadata)
--
-- object_id = '*'   grants access to all records of that resource.
-- object_id = '<n>' grants access only to the record whose PK equals <n>.
--
-- Resources correspond to simulator entity types:
--   customer    (IDs 1–1000)
--   store       (IDs 1–20)
--   product     (IDs 1–50)
--   order       (IDs 1–1000)
--   order_item  (IDs 1–5000)
--   payment     (IDs 1–2000)

USE ROLE SCHEMACHANGE_ROLE;

DROP VIEW IF EXISTS GOVERNANCE.SECURITY.V_ENTITLEMENTS;
DROP TABLE IF EXISTS GOVERNANCE.SECURITY.ENTITLEMENTS;

CREATE TABLE GOVERNANCE.SECURITY.ENTITLEMENTS (
    user_id INTEGER NOT NULL,
    resource VARCHAR(64) NOT NULL,
    access_level TINYINT NOT NULL CHECK (access_level IN (0, 1, 2)),
    object_id VARCHAR(16) NOT NULL,
    updated_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_entitlements PRIMARY KEY (user_id, resource, object_id)
);

-- user 1: data steward — full read access with PII across all resources
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS (user_id, resource, access_level, object_id) VALUES
(1, 'customer', 2, '*'),
(1, 'store', 2, '*'),
(1, 'product', 2, '*'),
(1, 'order', 2, '*'),
(1, 'order_item', 2, '*'),
(1, 'payment', 2, '*');

-- user 2: ops analyst — full read on orders/stores/products, no customer or payment access
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS (user_id, resource, access_level, object_id) VALUES
(2, 'store', 2, '*'),
(2, 'product', 2, '*'),
(2, 'order', 2, '*'),
(2, 'order_item', 2, '*');

-- user 3: CRM analyst — customer data with PII, read-only orders (no PII beyond what order carries)
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS (user_id, resource, access_level, object_id) VALUES
(3, 'customer', 1, '*'),
(3, 'order', 2, '*'),
(3, 'order_item', 2, '*');

-- user 4: store manager for store 5 — scoped to their own store record, all products, and orders
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS (user_id, resource, access_level, object_id) VALUES
(4, 'store', 2, '5'),
(4, 'product', 2, '*'),
(4, 'order', 2, '*'),
(4, 'order_item', 2, '*');

-- user 5: finance analyst — payment data with PII, read-all orders
INSERT INTO GOVERNANCE.SECURITY.ENTITLEMENTS (user_id, resource, access_level, object_id) VALUES
(5, 'payment', 1, '*'),
(5, 'order', 2, '*');

-- Convenience view used by masking / row-access policies
CREATE OR REPLACE VIEW GOVERNANCE.SECURITY.V_ENTITLEMENTS AS
SELECT
    user_id,
    resource,
    access_level,
    object_id
FROM GOVERNANCE.SECURITY.ENTITLEMENTS
WHERE access_level > 0;
