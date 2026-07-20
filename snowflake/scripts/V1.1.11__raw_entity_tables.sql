-- Entity-specific raw landing tables in BRONZE.RAW.
--
-- Each table is a thin landing zone: the full CloudEvent JSON is stored as-is
-- in record_content (VARIANT).  Column extraction and deduplication happen in
-- the Silver staging layer (staging_scd1 macro).
--
-- Schema (same for every entity table):
--   ingested_at    TIMESTAMP_LTZ  — wall-clock time the COPY ran
--   source_file    VARCHAR        — S3 file path (metadata$filename)
--   record_content VARIANT        — full CloudEvent JSON, unmodified
--
-- Populated by: copy_raw_events macro (dbt pre-hook on each staging model).
-- Deduplicated by: staging_scd1 macro (SCD-1, latest record_content:time wins).
--
-- Event types per table:
--   CUSTOMERS    com.dataplatform.ecommerce.customer.upserted
--   ORDER_ITEMS  com.dataplatform.ecommerce.order_item.upserted
--   ORDERS       com.dataplatform.ecommerce.order.upserted
--   PAYMENTS     com.dataplatform.ecommerce.payment.processed
--   PRODUCTS     com.dataplatform.ecommerce.product.upserted
--   STORES       com.dataplatform.ecommerce.store.upserted

USE ROLE SCHEMACHANGE_ROLE;

CREATE TABLE IF NOT EXISTS BRONZE.RAW.CUSTOMERS (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

CREATE TABLE IF NOT EXISTS BRONZE.RAW.ORDER_ITEMS (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

CREATE TABLE IF NOT EXISTS BRONZE.RAW.ORDERS (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

CREATE TABLE IF NOT EXISTS BRONZE.RAW.PAYMENTS (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

CREATE TABLE IF NOT EXISTS BRONZE.RAW.PRODUCTS (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

CREATE TABLE IF NOT EXISTS BRONZE.RAW.STORES (
    ingested_at    TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_file    VARCHAR,
    record_content VARIANT
);

