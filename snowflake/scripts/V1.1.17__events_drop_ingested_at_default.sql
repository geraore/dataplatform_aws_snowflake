-- Snowpipe Streaming rejects tables that have columns with a DEFAULT value.
-- Drop the default from ingested_at so Firehose can stream into BRONZE.RAW.EVENTS.
-- Firehose writes only to record_content and record_metadata; ingested_at will
-- be NULL for streaming rows. Use record_content:time (ce_time) for event timing.
USE ROLE SCHEMACHANGE_ROLE;

ALTER TABLE BRONZE.RAW.EVENTS ALTER COLUMN ingested_at DROP DEFAULT;
