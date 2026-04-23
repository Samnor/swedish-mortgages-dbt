-- Staged Swedish interest rates from the Riksbanken SWEA API.
-- Casts types, filters nulls, and deduplicates overlapping reloads.

with raw as (
    select
        cast(rate_date as date) as rate_date,
        trim(series_id) as series_id,
        trim(series_name) as series_name,
        trim(category) as category,
        cast(value as decimal(10, 4)) as value
    from {{ source('swedish_finance', 'se_rates_raw') }}
    where rate_date is not null
      and series_id is not null
      and value is not null
),

deduped as (
    select
        *,
        row_number() over (
            partition by rate_date, series_id
            order by rate_date
        ) as rn
    from raw
)

select
    rate_date,
    series_id,
    series_name,
    category,
    value
from deduped
where rn = 1

