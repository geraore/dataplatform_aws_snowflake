with source as (

    select * from {{ ref('raw_order_items') }}

),

renamed as (

    select
        id as order_item_id,
        order_id,
        product_id,
        quantity

    from source

)

select * from renamed
