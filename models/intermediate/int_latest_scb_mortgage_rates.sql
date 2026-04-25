-- Latest SCB MFI mortgage rates per loan type and fixing-period bucket.
-- Avoids dropping buckets when a newly published month is partial.

with ranked as (
    select
        period_month,
        period_date,
        loan_type,
        loan_type_name,
        period_code,
        period_label,
        rate,
        row_number() over (
            partition by loan_type, period_label
            order by period_date desc
        ) as rn
    from {{ ref('stg_scb_mortgage_rates') }}
)

select
    period_month,
    period_date,
    loan_type,
    loan_type_name,
    period_code,
    period_label,
    rate,
    date_diff('day', period_date, current_date) as scb_rate_age_days,
    case
        when date_diff('day', period_date, current_date) <= 45 then 'fresh'
        when date_diff('day', period_date, current_date) <= 75 then 'aging'
        else 'stale'
    end as scb_rate_freshness
from ranked
where rn = 1
