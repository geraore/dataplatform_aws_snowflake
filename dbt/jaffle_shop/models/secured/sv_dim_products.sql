select
    product_id,
    name,
    category,
    price

from {{ ref('dim_products') }}
