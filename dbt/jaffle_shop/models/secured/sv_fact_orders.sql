select
    order_id,
    customer_id,
    store_id,
    order_date,
    status,
    credit_card_amount,
    coupon_amount,
    bank_transfer_amount,
    gift_card_amount,
    amount

from {{ ref('fact_orders') }}
