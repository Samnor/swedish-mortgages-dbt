-- Staged bank listed mortgage rates scraped daily from SBAB, Nordea, Swedbank.
-- Deduplicates by keeping the earliest scrape per bank, period, and day.

with raw as (
    select *
    from {{ source('swedish_finance', 'bank_listed_rates_raw') }}
),

parsed as (
    select
        cast(date_parse(substr(scraped_at, 1, 10), '%Y-%m-%d') as date) as scrape_date,
        bank,
        period_label,
        cast(period_years as double) as period_years,
        cast(list_rate as double) as list_rate,
        cast(avg_rate as double) as avg_rate,
        valid_from,
        scraped_at,
        source
    from raw
    where list_rate is not null
),

deduped as (
    select
        *,
        row_number() over (
            partition by scrape_date, bank, period_label
            order by scraped_at
        ) as rn
    from parsed
)

select
    scrape_date,
    bank,
    period_label,
    period_years,
    list_rate,
    avg_rate,
    valid_from,
    scraped_at,
    source
from deduped
where rn = 1
order by scrape_date desc, bank, period_years

