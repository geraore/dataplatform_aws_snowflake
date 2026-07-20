{{ config(
    materialized = 'incremental',
    unique_key   = 'customer_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.customer.upserted') }}"
) }}

{{ staging_scd1(unique_key='customer_id') }}
