with date_spine as (

    select
        dateadd(day, seq4(), '2017-01-01'::date) as date_day
    from table(generator(rowcount => 365 * 10))

),

final as (

    select
        date_day,
        year(date_day)                                      as year,
        quarter(date_day)                                   as quarter,
        month(date_day)                                     as month,
        monthname(date_day)                                 as month_name,
        weekofyear(date_day)                                as week_of_year,
        day(date_day)                                       as day_of_month,
        dayofweek(date_day)                                 as day_of_week,
        dayname(date_day)                                   as day_name,
        iff(dayofweek(date_day) in (0, 6), true, false)    as is_weekend

    from date_spine

)

select * from final
