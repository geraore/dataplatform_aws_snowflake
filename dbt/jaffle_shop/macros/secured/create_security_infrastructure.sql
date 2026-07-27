{#
  create_security_infrastructure — idempotent creation of all Snowflake
  governance objects that back the secured views in models/secured/.

  Called via on-run-start in dbt_project.yml so every object exists before any
  secured view model is built and its post-hook fires.

  Session context
  ---------------
  The application sets  SET app_user_id = <integer>;  before running queries.
  Policies read it with  GETVARIABLE('app_user_id')::INTEGER.
  If the variable is not set, GETVARIABLE returns NULL → no access (deny-by-default).

  Objects created in GOVERNANCE.SECURITY (schema exists from V1.1.4):

    MASK_<RESOURCE>_PII_STRING          VARCHAR masking policy
                                        → val shown at access_level >= 1, else '***'

    MASK_<RESOURCE>_FINANCIAL_NUMBER    NUMBER masking policy
                                        → val shown at access_level >= 2, else NULL

    RAP_<RESOURCE>                      row access policy
                                        → row visible when user has access_level > 0
                                          and object_id matches '*' or the row PK

  Resources: customer, store, product, order, order_item, payment.
  dim_date is a pure calendar dimension — no row or column restrictions.
#}

{% macro create_security_infrastructure() %}

{% if execute %}

{# ------------------------------------------------------------------ #}
{# Per-resource masking and row-access policies                        #}
{# ------------------------------------------------------------------ #}
{#
   pii_string  → need a VARCHAR masking policy (access_level >= 1)
   financial   → need a NUMBER  masking policy (access_level >= 2)
   pk_type     → Snowflake type of the PK column passed to the RAP
#}
{% set resources = {
    'customer':   {'pii_string': true,  'financial': true,  'pk_type': 'INTEGER'},
    'store':      {'pii_string': false, 'financial': false, 'pk_type': 'INTEGER'},
    'product':    {'pii_string': false, 'financial': true,  'pk_type': 'INTEGER'},
    'order':      {'pii_string': false, 'financial': true,  'pk_type': 'INTEGER'},
    'order_item': {'pii_string': false, 'financial': true,  'pk_type': 'INTEGER'},
    'payment':    {'pii_string': false, 'financial': true,  'pk_type': 'INTEGER'},
} %}

{% for resource, cfg in resources.items() %}

  {% if cfg.pii_string %}
  {% set mask_pii %}
CREATE MASKING POLICY IF NOT EXISTS
    GOVERNANCE.SECURITY.MASK_{{ resource | upper }}_PII_STRING
AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM   GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = '{{ resource }}'
              AND  access_level >= 1
        ) THEN val
        ELSE '***'
    END;
  {% endset %}
  {% do run_query(mask_pii) %}
  {% do log("security: created MASK_" ~ resource | upper ~ "_PII_STRING", info=true) %}
  {% endif %}

  {% if cfg.financial %}
  {% set mask_fin %}
CREATE MASKING POLICY IF NOT EXISTS
    GOVERNANCE.SECURITY.MASK_{{ resource | upper }}_FINANCIAL_NUMBER
AS (val NUMBER) RETURNS NUMBER ->
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM   GOVERNANCE.SECURITY.ENTITLEMENTS
            WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
              AND  resource     = '{{ resource }}'
              AND  access_level >= 2
        ) THEN val
        ELSE NULL
    END;
  {% endset %}
  {% do run_query(mask_fin) %}
  {% do log("security: created MASK_" ~ resource | upper ~ "_FINANCIAL_NUMBER", info=true) %}
  {% endif %}

  {% set create_rap %}
CREATE ROW ACCESS POLICY IF NOT EXISTS
    GOVERNANCE.SECURITY.RAP_{{ resource | upper }}
AS (object_pk {{ cfg.pk_type }}) RETURNS BOOLEAN ->
    GETVARIABLE('app_user_id') IS NOT NULL
    AND EXISTS (
        SELECT 1
        FROM   GOVERNANCE.SECURITY.ENTITLEMENTS
        WHERE  user_id      = GETVARIABLE('app_user_id')::INTEGER
          AND  resource     = '{{ resource }}'
          AND  access_level > 0
          AND  (object_id = '*' OR object_id = object_pk::VARCHAR)
    );
  {% endset %}
  {% do run_query(create_rap) %}
  {% do log("security: created RAP_" ~ resource | upper, info=true) %}

{% endfor %}

{% do log("security: infrastructure ready", info=true) %}

{% endif %}

{% endmacro %}
