{#
    Native Snowflake SEMANTIC VIEW over the gold marts, queryable by Cortex
    Analyst. Built as a first-class dbt model via the `semantic_view`
    materialization from Snowflake-Labs/dbt_semantic_view, so it participates in
    `dbt build` and depends on the marts through ref() (no run-operation needed).

    The model name -> relation: GOLD.MARTS.SEM_JAFFLE (per dbt_project.yml routing).
    The body below is passed through to Snowflake's CREATE SEMANTIC VIEW syntax:
    https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view#syntax
#}

{{ config(materialized='semantic_view') }}

TABLES (
    customers AS {{ ref('customers') }}
        PRIMARY KEY (customer_id)
        WITH SYNONYMS ('clients', 'buyers')
        COMMENT = 'Jaffle shop customers',
    orders AS {{ ref('orders') }}
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
COMMENT = 'Semantic view over jaffle shop marts for Cortex Analyst'
