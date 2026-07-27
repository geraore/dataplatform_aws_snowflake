{#
    apply_governance — superseded by the secured views in models/secured/.

    The secured views (sv_dim_*, sv_fact_*) carry their own post-hooks that
    attach Snowflake row access policies and column masking policies driven by
    GOVERNANCE.SECURITY.ENTITLEMENTS.  Security infrastructure (policies) is
    created automatically via on-run-start → create_security_infrastructure().

    This macro is kept for backwards compatibility with any existing runbooks.
    It is now a no-op; run `dbt run --select secured` to rebuild the views and
    reattach all policies.
#}

{% macro apply_governance() %}
    {% do log(
        "apply_governance is a no-op. Policies are attached via post-hooks on "
        ~ "the secured views (models/secured/). Run: dbt run --select secured",
        info=true
    ) %}
{% endmacro %}
