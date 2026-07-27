{{ config(
    materialized = 'incremental',
    unique_key   = 'store_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.store') }}"
) }}

{{ staging_scd1(unique_key='store_id') }}
