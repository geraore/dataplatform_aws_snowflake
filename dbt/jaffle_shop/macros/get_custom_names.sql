{#
    Make +database / +schema literal.

    By default dbt prefixes custom schemas with the target schema (e.g.
    "analytics_STAGING"). For the medallion layout we want the exact names
    BRONZE.RAW, SILVER.STAGING, GOLD.MARTS, so we override both resolvers to
    use the configured value verbatim.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

{% macro generate_database_name(custom_database_name, node) -%}
    {%- if custom_database_name is none -%}
        {{ target.database }}
    {%- else -%}
        {{ custom_database_name | trim }}
    {%- endif -%}
{%- endmacro %}
