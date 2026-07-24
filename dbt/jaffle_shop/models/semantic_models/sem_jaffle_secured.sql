{#
    Native Snowflake SEMANTIC VIEW over the secured views in GOLD.MARTS.
    Mirrors sem_jaffle but targets the sv_* secured views so that column
    masking and row-access policies defined in GOVERNANCE.SECURITY are
    enforced at query time via Cortex Analyst.
#}

{{ config(materialized='semantic_view') }}

TABLES (
    customers AS GOLD.MARTS.sv_dim_customers
        PRIMARY KEY (customer_id)
        WITH SYNONYMS ('clients', 'buyers')
        COMMENT = 'Jaffle shop customers (secured)',
    orders AS GOLD.MARTS.sv_fact_orders
        PRIMARY KEY (order_id)
        COMMENT = 'Jaffle shop orders (secured)',
    order_items AS GOLD.MARTS.sv_fact_order_items
        PRIMARY KEY (order_item_id)
        WITH SYNONYMS ('line items', 'order lines')
        COMMENT = 'Order line items — most granular grain (secured)',
    products AS GOLD.MARTS.sv_dim_products
        PRIMARY KEY (product_id)
        WITH SYNONYMS ('items', 'menu items')
        COMMENT = 'Jaffle shop product catalogue (secured)',
    dates AS GOLD.MARTS.sv_dim_date
        PRIMARY KEY (date_day)
        WITH SYNONYMS ('calendar', 'time')
        COMMENT = 'Calendar date dimension (secured)',
    stores AS GOLD.MARTS.sv_dim_stores
        PRIMARY KEY (store_id)
        WITH SYNONYMS ('locations', 'branches')
        COMMENT = 'Physical store locations (secured)'
)
RELATIONSHIPS (
    orders_to_customers AS
        orders (customer_id) REFERENCES customers (customer_id),
    order_items_to_orders AS
        order_items (order_id) REFERENCES orders (order_id),
    order_items_to_products AS
        order_items (product_id) REFERENCES products (product_id),
    orders_to_dates AS
        orders (order_date) REFERENCES dates (date_day),
    orders_to_stores AS
        orders (store_id) REFERENCES stores (store_id)
)
FACTS (
    orders.amount AS amount,
    order_items.quantity AS quantity,
    order_items.line_total AS line_total,
    order_items.unit_price AS unit_price
)
DIMENSIONS (
    customers.first_name AS first_name,
    customers.last_name AS last_name,
    orders.status AS status,
    orders.order_date AS order_date,
    products.name AS name,
    products.category AS category,
    dates.year AS year,
    dates.quarter AS quarter,
    dates.month_name AS month_name,
    dates.is_weekend AS is_weekend,
    stores.name AS name,
    stores.city AS city,
    stores.state AS state,
    stores.country AS country
)
METRICS (
    orders.total_revenue AS SUM(orders.amount),
    orders.order_count AS COUNT(orders.order_id),
    customers.customer_count AS COUNT(DISTINCT customers.customer_id),
    order_items.total_product_revenue AS SUM(order_items.line_total),
    order_items.total_units_sold AS SUM(order_items.quantity)
)
COMMENT = 'Secured semantic view over jaffle shop marts for Cortex Analyst — enforces ABAC masking and row-access policies'
