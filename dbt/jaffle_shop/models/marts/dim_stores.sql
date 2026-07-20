with stores as (

    select * from {{ ref('stores') }}

),

final as (

    select
        store_id,
        name,
        city,
        state,
        country

    from stores

)

select * from final
