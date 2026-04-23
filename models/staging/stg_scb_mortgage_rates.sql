-- Staged SCB MFI monthly average mortgage rates.
-- Covers new loans and outstanding loans since 2020-01.

with raw as (
    select *
    from {{ source('swedish_finance', 'scb_mortgage_rates_raw') }}
),

parsed as (
    select
        period_month,
        loan_type,
        loan_type_name,
        period_code,
        period_label,
        cast(rate as double) as rate
    from raw
    where rate is not null
),

deduped as (
    select
        *,
        row_number() over (
            partition by period_month, loan_type, period_code
            order by period_month
        ) as rn
    from parsed
)

select
    period_month,
    cast(date_parse(period_month || '-01', '%Y-%m-%d') as date) as period_date,
    loan_type,
    loan_type_name,
    period_code,
    period_label,
    rate
from deduped
where rn = 1
order by period_month desc, loan_type, period_code

