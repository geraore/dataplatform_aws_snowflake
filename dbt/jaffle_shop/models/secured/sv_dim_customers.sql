select
    customer_id,
    first_name,
    last_name,
    first_order,
    most_recent_order,
    number_of_orders,
    customer_lifetime_value

from {{ ref('dim_customers') }}
