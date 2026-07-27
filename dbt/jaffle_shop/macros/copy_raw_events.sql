{#
  copy_raw_events — load raw CloudEvents from S3 into a BRONZE.RAW entity table.

  Called as a dbt pre-hook on each staging model.  The target table is derived
  from the calling model's identifier (this.identifier), so one macro handles
  all entities.

  Raw table schema (created by schemachange V1.1.11):
    ingested_at    TIMESTAMP_LTZ  — wall-clock time the COPY ran
    source_file    VARCHAR        — S3 file path (metadata$filename)
    record_content VARIANT        — full CloudEvent JSON, unmodified

  S3 layout written by Firehose:
    events/<event_type>/<yyyy>/<MM>/<dd>/<file>.jsonl

  Snowflake deduplicates by file (LOAD_HISTORY, 64-day window), so re-running
  the same COPY will not insert duplicate rows unless FORCE = TRUE is used.

  Parameters
  ----------
  event_type  string  Entity-level S3 prefix — the CloudEvent type up to but
                      not including the action suffix (.upsert / .delete), e.g.
                      'com.dataplatform.ecommerce.customer'.
                      Firehose strips the action suffix before writing to S3,
                      so this prefix captures both upsert and delete events.

  Usage (in staging model config)
  --------------------------------
  {{ config(
      pre_hook = "{{ copy_raw_events('com.dataplatform.ecommerce.customer') }}"
  ) }}
#}

{% macro copy_raw_events(event_type) %}
{% if not execute %}{{ return('') }}{% endif %}
COPY INTO BRONZE.RAW.{{ this.identifier }} (ingested_at, source_file, record_content)
FROM (
    SELECT
        CURRENT_TIMESTAMP(),
        metadata$filename,
        $1::VARIANT
    FROM @BRONZE.RAW.EVENTS_S3_STAGE/{{ event_type }}/
)
FILE_FORMAT = (TYPE = JSON STRIP_OUTER_ARRAY = FALSE)
ON_ERROR = CONTINUE
{% endmacro %}
