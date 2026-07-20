{{ config(
    materialized = 'incremental',
    unique_key   = 'order_item_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.order_item.upserted') }}"
) }}

{{ staging_scd1(unique_key='order_item_id') }}
