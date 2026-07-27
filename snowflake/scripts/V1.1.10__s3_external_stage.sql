-- External stage over the events S3 bucket + grants for COPY commands.
--
-- The S3 URL is templated from CDK_DEFAULT_ACCOUNT (set in .env).
-- The stage re-uses the EVENTS_S3_INT storage integration from V1.1.9.
--
-- COPY pattern (run as DBT_ROLE or SCHEMACHANGE_ROLE):
--
--   -- All events in a given day:
--   COPY INTO BRONZE.RAW.EVENTS (record_content, ingested_at)
--   FROM (
--       SELECT $1::VARIANT, CURRENT_TIMESTAMP()
--       FROM @BRONZE.RAW.EVENTS_S3_STAGE/events/ecommerce_clicks/2026/07/15/
--   )
--   FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = FALSE)
--   ON_ERROR = 'CONTINUE';
--
--   -- All events of a given type across all time:
--   COPY INTO BRONZE.RAW.EVENTS (record_content, ingested_at)
--   FROM (
--       SELECT $1::VARIANT, CURRENT_TIMESTAMP()
--       FROM @BRONZE.RAW.EVENTS_S3_STAGE/events/ecommerce_clicks/
--   )
--   FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = FALSE)
--   ON_ERROR = 'CONTINUE';
--
-- Files are deduplicated by Snowflake for 64 days (LOAD_HISTORY); re-running
-- the same COPY will not duplicate rows unless you set FORCE = TRUE.
USE ROLE SCHEMACHANGE_ROLE;

CREATE STAGE IF NOT EXISTS BRONZE.RAW.EVENTS_S3_STAGE
    URL = 's3://dataplatform-events-{{ env_var("CDK_DEFAULT_ACCOUNT") }}/events/'
    STORAGE_INTEGRATION = EVENTS_S3_INT
    FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = FALSE)
    COMMENT = 'External stage over the events S3 bucket (dynamic-partitioned JSONL)';

-- DBT_ROLE runs COPY commands in dbt seeds/macros and ad-hoc loads.
GRANT USAGE ON STAGE BRONZE.RAW.EVENTS_S3_STAGE TO ROLE DBT_ROLE;
-- COPY INTO requires INSERT on the target table.
GRANT INSERT ON TABLE BRONZE.RAW.EVENTS TO ROLE DBT_ROLE;

-- Let SCHEMACHANGE_ROLE also list and query the stage for diagnostics.
GRANT USAGE ON STAGE BRONZE.RAW.EVENTS_S3_STAGE TO ROLE SCHEMACHANGE_ROLE;
