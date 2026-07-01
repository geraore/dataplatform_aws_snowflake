{#
    Attach the ABAC masking policy (from snowflake/V1.1.5) to PII columns on the
    gold marts. Run after `dbt build`:

        dbt run-operation apply_governance

    The policy itself is owned by schemachange; here we only bind it to the
    columns dbt materializes, so re-running a model does not lose the binding.
#}

{% macro apply_governance() %}
    {% set statements = [
        "ALTER TABLE GOLD.MARTS.CUSTOMERS
            MODIFY COLUMN first_name SET MASKING POLICY GOVERNANCE.SECURITY.MASK_PII_STRING",
        "ALTER TABLE GOLD.MARTS.CUSTOMERS
            MODIFY COLUMN last_name SET MASKING POLICY GOVERNANCE.SECURITY.MASK_PII_STRING"
    ] %}

    {% for stmt in statements %}
        {% do log("Applying: " ~ stmt, info=true) %}
        {% do run_query(stmt) %}
    {% endfor %}
    {% do log("Governance policies applied.", info=true) %}
{% endmacro %}
