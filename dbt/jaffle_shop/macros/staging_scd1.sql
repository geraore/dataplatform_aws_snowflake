{#
  staging_scd1 — render SCD-1 incremental SQL for a staging model.

  Column list is driven by the model's YAML definition (model.columns).
  Each column must declare a data_type so the macro can cast from VARIANT.

  Source convention
  -----------------
  Raw table is resolved via {{ source('raw', this.identifier) }}, which maps
  to BRONZE.RAW.<model_name> as declared in models/staging/sources.yml.
  The raw table stores each CloudEvent as a single VARIANT (record_content).

  Column extraction
  -----------------
  CE envelope fields (ce_id, ce_time, ce_type, ce_source, ce_specversion,
  ce_subject) are extracted from the top-level CloudEvent attributes.
  All other columns are extracted from record_content:data:<col_name>.
  Types come from the data_type defined in the model's YAML columns.

  Incremental strategy
  --------------------
  Filters the raw table to rows whose record_content:time is at or after
  (staging max ce_time_col − lookback_seconds).  The look-back guards against
  late-arriving events at the Firehose boundary.

  Deduplication
  -------------
  QUALIFY row_number() keeps the latest event per entity
  (highest record_content:time wins — SCD-1, last write wins).

  Parameters
  ----------
  unique_key       string | list   Column(s) identifying one entity record.
                                   Must match the unique_key set in config().
  ce_time_col      string          Name of the timestamp column in THIS (the
                                   staging table) used for the incremental
                                   look-back filter.  Default: 'ce_time'.
  lookback_seconds int             Seconds subtracted from staging max timestamp.
                                   Default: 15.

  Usage
  -----
  -- models/staging/customers.sql
  {{ config(
      materialized = 'incremental',
      unique_key   = 'customer_id',
      pre_hook     = "{{ copy_raw_events('com.dataplatform.ecommerce.customer.upserted') }}"
  ) }}
  {{ staging_scd1(unique_key='customer_id') }}

  -- models/staging/customers.yml (data_type drives the VARIANT cast)
  columns:
    - name: customer_id
      data_type: integer
    - name: first_name
      data_type: varchar
    - name: last_name
      data_type: varchar
    - name: ce_time
      data_type: timestamp_tz
#}

{% macro staging_scd1(unique_key, ce_time_col='ce_time', lookback_seconds=15) %}

{% if not execute %}{{ return('') }}{% endif %}

{%- set uk_cols    = [unique_key] if unique_key is string else unique_key -%}
{%- set raw_source = source('raw', this.identifier) -%}
{%- set col_names  = model.columns.keys() | list -%}

{#- Well-known CloudEvents 1.0 envelope attributes → VARIANT path in record_content -#}
{%- set ce_envelope = {
    'ce_id':          'record_content:id',
    'ce_type':        'record_content:type',
    'ce_source':      'record_content:source',
    'ce_specversion': 'record_content:specversion',
    'ce_time':        'record_content:time',
    'ce_subject':     'record_content:subject',
} -%}

with source as (

    select
        {%- for col in col_names %}
        {%- set col_info  = model.columns[col] %}
        {%- set cast_type = col_info.data_type | upper if col_info.data_type else 'VARIANT' %}
        {%- if col in ce_envelope %}
        {{ ce_envelope[col] }}::{{ cast_type }} as {{ col }}
        {%- else %}
        record_content:data:{{ col }}::{{ cast_type }} as {{ col }}
        {%- endif %}
        {%- if not loop.last %},{% endif %}

        {%- endfor %}
    from {{ raw_source }}
    {%- if is_incremental() %}

    where record_content:time::TIMESTAMP_TZ >= coalesce((
        select dateadd('second', -{{ lookback_seconds }}, max({{ ce_time_col }}))
        from {{ this }}
    ), '1970-01-01'::TIMESTAMP_TZ)
    {%- endif %}

    qualify row_number() over (
        partition by {{ uk_cols | join(', ') }}
        order by record_content:time::TIMESTAMP_TZ desc
    ) = 1

)

select * from source

{% endmacro %}
