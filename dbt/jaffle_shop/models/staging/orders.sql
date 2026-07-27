{{ config(
    materialized = 'incremental',
    unique_key   = 'order_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.order') }}"
) }}

{{ staging_scd1(unique_key='order_id') }}
