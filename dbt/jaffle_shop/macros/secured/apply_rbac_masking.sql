{#
  apply_rbac_masking — post-hook that attaches RBAC-based masking policies
  to mart tables (not views). Masking is driven by the GOLD.NO_PII database
  role being active in the session, with no ABAC session variable required.

  Wire it up in the model's schema.yml config:

      config:
        post_hook:
          - "{{ apply_rbac_masking(this, model) }}"

  Mark columns that carry PII in the model YAML:

      columns:
        - name: first_name
          data_type: varchar
          meta:
            security:
              pii: true

  varchar / char / text / string → GOVERNANCE.SECURITY.MASK_NO_PII_STRING
  All numeric types           → GOVERNANCE.SECURITY.MASK_NO_PII_NUMBER
#}

{% macro apply_rbac_masking(relation, model_node) %}

{% if execute %}

{% set _string_prefixes = ['varchar', 'char', 'nvarchar', 'nchar', 'text', 'string'] %}

{% for col_name, col_info in model_node.get('columns', {}).items() %}
  {% set sec = col_info.get('meta', {}).get('security', none) %}
  {% if sec and sec.get('pii') %}

    {% set data_type = col_info.get('data_type', 'varchar') | string | lower | trim %}

    {% set ns = namespace(is_string=false) %}
    {% for prefix in _string_prefixes %}
      {% if data_type.startswith(prefix) %}
        {% set ns.is_string = true %}
      {% endif %}
    {% endfor %}

    {% if ns.is_string %}
      {% set policy = 'GOVERNANCE.SECURITY.MASK_NO_PII_STRING' %}
    {% else %}
      {% set policy = 'GOVERNANCE.SECURITY.MASK_NO_PII_NUMBER' %}
    {% endif %}

    {% do run_query(
        "ALTER TABLE " ~ relation
        ~ " MODIFY COLUMN " ~ col_name
        ~ " SET MASKING POLICY " ~ policy
    ) %}
    {% do log("apply_rbac_masking: " ~ col_name ~ " → " ~ policy, info=true) %}

  {% endif %}
{% endfor %}

{% endif %}

{{ return('SELECT 1') }}

{% endmacro %}
