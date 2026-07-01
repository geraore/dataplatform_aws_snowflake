{#
    Create a native Snowflake SEMANTIC VIEW over the gold marts so it can be
    queried by Cortex Analyst. Run after `dbt build`:

        dbt run-operation create_semantic_views

    Kept as a run-operation (rather than a model) because SEMANTIC VIEW is not a
    dbt materialization; this way it still lives with the models it depends on.
#}

{% macro create_semantic_views() %}
    {% set sql %}
        CREATE OR REPLACE SEMANTIC VIEW GOLD.MARTS.SEM_JAFFLE
            TABLES (
                customers AS GOLD.MARTS.CUSTOMERS
                    PRIMARY KEY (customer_id)
                    WITH SYNONYMS ('clients', 'buyers')
                    COMMENT = 'Jaffle shop customers',
                orders AS GOLD.MARTS.ORDERS
                    PRIMARY KEY (order_id)
                    COMMENT = 'Jaffle shop orders'
            )
            RELATIONSHIPS (
                orders_to_customers AS
                    orders (customer_id) REFERENCES customers (customer_id)
            )
            FACTS (
                orders.order_amount AS amount
            )
            DIMENSIONS (
                customers.customer_first_name AS first_name,
                customers.customer_last_name AS last_name,
                orders.order_status AS status,
                orders.order_date AS order_date
            )
            METRICS (
                orders.total_revenue AS SUM(orders.order_amount),
                orders.order_count AS COUNT(orders.order_id),
                customers.customer_count AS COUNT(DISTINCT customers.customer_id)
            )
            COMMENT = 'Semantic view over jaffle shop marts for Cortex Analyst';
    {% endset %}

    {% do log("Creating semantic view GOLD.MARTS.SEM_JAFFLE", info=true) %}
    {% do run_query(sql) %}
    {% do log("Done.", info=true) %}
{% endmacro %}
