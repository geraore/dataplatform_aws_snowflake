{#
  staging_scd1 — render SCD-1 incremental SQL for a staging model.

  Column list is driven entirely by the model's YAML definition (model.columns),
  so schema changes are declared once in the .yml file and the SQL stays in sync
  automatically.

  Source convention
  -----------------
  Raw table is always BRONZE.RAW.<model_name> — the same identifier as the
  staging model, matching the project naming convention.

  Incremental strategy
  --------------------
  Filters the raw table to rows whose CE_TIME is at or after
  (staging max CE_TIME − lookback_seconds).  The look-back guards against
  late-arriving events at the Firehose boundary.  dbt merges into the staging
  table using the unique_key.

  Deduplication
  -------------
  ROW_NUMBER() keeps the latest event per entity (highest CE_TIME wins).

  Parameters
  ----------
  unique_key       string | list   Column(s) identifying one entity record.
                                   Must match the unique_key set in config().
  ce_time_col      string          CloudEvent envelope timestamp column.
                                   Default: 'CE_TIME'.
  lookback_seconds int             Seconds subtracted from staging max timestamp
                                   for the incremental filter.  Default: 15.

  Usage
  -----
  -- models/staging/stg_customers.sql
  {{ config(materialized='incremental', unique_key='customer_id') }}
  {{ staging_scd1(unique_key='customer_id') }}

  -- models/staging/stg_customers.yml (columns drive the SELECT list)
  columns:
    - name: customer_id
    - name: first_name
    - name: last_name
    - name: ce_time
#}

{% macro staging_scd1(unique_key, ce_time_col='CE_TIME', lookback_seconds=15) %}

{% if not execute %}{{ return('') }}{% endif %}

{%- set uk_cols   = [unique_key] if unique_key is string else unique_key -%}
{%- set raw_table = 'BRONZE.RAW.' ~ this.identifier -%}
{%- set col_names = model.columns.keys() | list -%}

with source as (

    select
        {%- for col in col_names %}
        {{ col }}{% if not loop.last %},{% endif %}

        {%- endfor %}
    from {{ raw_table }}
    {%- if is_incremental() %}

    where {{ ce_time_col }} >= (
        select dateadd('second', -{{ lookback_seconds }}, max({{ ce_time_col }}))
        from {{ this }}
    )
    {%- endif %}

    qualify row_number() over (
        partition by {{ uk_cols | join(', ') }}
        order by {{ ce_time_col }} desc
    ) = 1

)

select * from source

{% endmacro %}
