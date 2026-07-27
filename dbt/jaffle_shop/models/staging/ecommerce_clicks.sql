{{
    config(
        materialized        = 'dynamic_table',
        snowflake_warehouse = 'DBT_WH',
        target_lag          = '1 minute',
        refresh_mode        = 'AUTO',
    )
}}

SELECT
    record_content:id::VARCHAR               AS ce_id,
    record_content:time::TIMESTAMP_TZ        AS ce_time,
    record_content:source::VARCHAR           AS ce_source,
    record_content:data:click_id::VARCHAR    AS click_id,
    record_content:data:session_id::INTEGER  AS session_id,
    record_content:data:customer_id::INTEGER AS customer_id,
    record_content:data:product_id::INTEGER  AS product_id,
    record_content:data:page_type::VARCHAR   AS page_type,
    record_content:data:action::VARCHAR      AS action,
    record_content:data:device_type::VARCHAR AS device_type,
    record_content:data:referrer::VARCHAR    AS referrer,
    ingested_at
FROM {{ source('raw', 'events') }}
WHERE record_content:type::VARCHAR = 'ecommerce_clicks'
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY record_content:data:click_id::VARCHAR
    ORDER BY record_content:time::TIMESTAMP_TZ DESC
) = 1
