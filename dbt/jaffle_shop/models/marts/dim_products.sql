with products as (

    select * from {{ ref('products') }}

),

final as (

    select
        product_id,
        name,
        category,
        price

    from products

)

select * from final
