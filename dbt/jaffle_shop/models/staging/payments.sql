{{ config(
    materialized = 'incremental',
    unique_key   = 'payment_id',
    pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.payment.processed') }}"
) }}

{{ staging_scd1(unique_key='payment_id') }}
