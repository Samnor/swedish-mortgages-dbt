-- Latest listed bank mortgage rates per bank and fixing period.
-- Keeps banks visible even when one scraper lags behind the others.

with ranked as (
    select
        scrape_date,
        bank,
        period_label,
        period_years,
        list_rate,
        avg_rate,
        valid_from,
        scraped_at,
        source,
        row_number() over (
            partition by bank, period_label
            order by scrape_date desc, scraped_at desc
        ) as rn
    from {{ ref('stg_bank_listed_rates') }}
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
    source,
    date_diff('day', scrape_date, current_date) as listed_rate_age_days,
    case
        when date_diff('day', scrape_date, current_date) <= 1 then 'fresh'
        when date_diff('day', scrape_date, current_date) <= 3 then 'aging'
        else 'stale'
    end as listed_rate_freshness
from ranked
where rn = 1
