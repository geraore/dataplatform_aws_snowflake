{#
  apply_column_masking — post-hook that applies Snowflake column masking
  policies to a secured view. The masking policy is derived from the column's
  data_type, so the column meta only needs to declare the resource.

  Row access policies are handled natively by dbt-snowflake (>=1.10) via
  config.row_access_policy in schema.yml — no macro needed for those.

  Wire it up in the model's schema.yml config (only for models that have
  columns with meta.security):

      config:
        post_hook:
          - "{{ apply_column_masking(this, model) }}"

  ── Column meta structure ────────────────────────────────────────────────────

      columns:
        - name: first_name
          data_type: varchar             # string type  → _PII_STRING
          meta:
            security:
              resource: customer

        - name: customer_lifetime_value
          data_type: number              # non-string   → _FINANCIAL_NUMBER
          meta:
            security:
              resource: customer

  ── data_type → masking policy mapping ──────────────────────────────────────

    varchar / char / text / string / nvarchar / nchar / binary / varbinary
      → GOVERNANCE.SECURITY.MASK_<RESOURCE>_PII_STRING    (masked as '***')

    All other types (number, float, integer, decimal, boolean, date, …)
      → GOVERNANCE.SECURITY.MASK_<RESOURCE>_FINANCIAL_NUMBER  (masked as NULL)

  Columns with no meta.security are left unmasked.

  ── Policy naming convention ─────────────────────────────────────────────────

  Policies are created by create_security_infrastructure (on-run-start):
    GOVERNANCE.SECURITY.MASK_<RESOURCE>_PII_STRING
    GOVERNANCE.SECURITY.MASK_<RESOURCE>_FINANCIAL_NUMBER
#}

{% macro apply_column_masking(relation, model_node) %}

{% if execute %}

{# String types that map to the PII_STRING masking policy. #}
{% set _string_prefixes = ['varchar', 'char', 'nvarchar', 'nchar', 'text', 'string', 'binary', 'varbinary'] %}

{% for col_name, col_info in model_node.get('columns', {}).items() %}
  {#
    dbt 1.10+ merges config.meta into col.meta at parse time, so reading
    col_info.meta is sufficient regardless of where meta was declared in YAML.
  #}
  {% set sec = col_info.get('meta', {}).get('security', none) %}
  {% if sec %}

    {% set resource   = sec.get('resource') %}
    {% set data_type  = col_info.get('data_type', '') | string | lower | trim %}

    {# Derive masking suffix from the column's declared data_type. #}
    {% set ns = namespace(is_string=false) %}
    {% for prefix in _string_prefixes %}
      {% if data_type.startswith(prefix) %}
        {% set ns.is_string = true %}
      {% endif %}
    {% endfor %}

    {% if ns.is_string %}
      {% set policy = 'GOVERNANCE.SECURITY.MASK_' ~ resource | upper ~ '_PII_STRING' %}
    {% else %}
      {% set policy = 'GOVERNANCE.SECURITY.MASK_' ~ resource | upper ~ '_FINANCIAL_NUMBER' %}
    {% endif %}

    {% do run_query(
        "ALTER VIEW " ~ relation
        ~ " MODIFY COLUMN " ~ col_name
        ~ " SET MASKING POLICY " ~ policy
    ) %}
    {% do log("apply_column_masking: " ~ col_name ~ " (" ~ data_type ~ ") → " ~ policy, info=true) %}

  {% endif %}
{% endfor %}

{% endif %}

{{ return('SELECT 1') }}

{% endmacro %}
