with order_items as (

    select * from {{ ref('order_items') }}

),

products as (

    select * from {{ ref('dim_products') }}

),

final as (

    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        oi.quantity,
        p.price                         as unit_price,
        oi.quantity * p.price           as line_total

    from order_items oi

    left join products p
        on oi.product_id = p.product_id

)

select * from final
