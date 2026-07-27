select
    store_id,
    name,
    city,
    state,
    country

from {{ ref('dim_stores') }}
