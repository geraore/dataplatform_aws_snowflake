with source as (

    select * from {{ ref('raw_stores') }}

),

renamed as (

    select
        id as store_id,
        name,
        city,
        state,
        country

    from source

)

select * from renamed
