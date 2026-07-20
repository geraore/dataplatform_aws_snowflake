{{ config(
    materialized = 'incremental',
    unique_key   = 'product_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.product.upserted') }}"
) }}

{{ staging_scd1(unique_key='product_id') }}
