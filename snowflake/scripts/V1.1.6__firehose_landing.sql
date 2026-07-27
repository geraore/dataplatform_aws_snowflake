-- Landing table that Firehose (Snowpipe Streaming) writes into.
--
-- Firehose is configured with VARIANT_CONTENT_MAPPING: the full event JSON goes
-- into RECORD_CONTENT and Firehose/Kinesis metadata into RECORD_METADATA.
USE ROLE SCHEMACHANGE_ROLE;

CREATE TABLE IF NOT EXISTS BRONZE.RAW.EVENTS (
    record_content VARIANT,
    record_metadata VARIANT,
    ingested_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Firehose ingests as FIREHOSE_ROLE; grant it just what it needs.
GRANT USAGE ON DATABASE BRONZE TO ROLE FIREHOSE_ROLE;
GRANT USAGE ON SCHEMA BRONZE.RAW TO ROLE FIREHOSE_ROLE;
GRANT INSERT ON TABLE BRONZE.RAW.EVENTS TO ROLE FIREHOSE_ROLE;
