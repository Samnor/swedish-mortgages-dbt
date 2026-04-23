-- Bank listed rates versus SCB MFI market-average rates and funding-cost proxies.

with latest_market as (
    select
        rate_date as funding_date,
        policy_rate,
        mortbond_2y,
        mortbond_5y
    from {{ ref('rates_daily') }}
    where rate_date = (
        select max(rate_date)
        from {{ ref('rates_daily') }}
        where mortbond_5y is not null
    )
),

latest_listed as (
    select
        bank,
        period_label as period_label_display,
        period_years,
        list_rate
    from {{ ref('stg_bank_listed_rates') }}
    where scrape_date = (
        select max(scrape_date)
        from {{ ref('stg_bank_listed_rates') }}
    )
),

latest_scb as (
    select
        period_label,
        max(case when loan_type = '0100' then rate end) as new_loan_rate,
        max(case when loan_type = '0200' then rate end) as outstanding_rate,
        max(period_month) as scb_period_month
    from {{ ref('stg_scb_mortgage_rates') }}
    where period_month = (
        select max(period_month)
        from {{ ref('stg_scb_mortgage_rates') }}
    )
    group by period_label
)

select
    l.bank,
    case cast(round(l.period_years * 4) as integer)
        when 1 then '0.25Y'
        when 4 then '01Y'
        when 8 then '02Y'
        when 12 then '03Y'
        when 16 then '04Y'
        when 20 then '05Y'
        when 24 then '06Y'
        when 28 then '07Y'
        when 32 then '08Y'
        when 36 then '09Y'
        when 40 then '10Y'
        else lpad(cast(cast(round(l.period_years * 12) as integer) as varchar), 3, '0') || 'M'
    end as period_label,
    l.period_label_display,
    l.period_years,
    case
        when l.period_years = 0.25 then '3M'
        when l.period_years = 1.0 then '1Y'
        when l.period_years = 2.0 then '2Y'
        when l.period_years >= 3.0 and l.period_years <= 5.0 then '3-5Y'
        when l.period_years > 5.0 then '5Y+'
    end as scb_bucket,
    l.list_rate,
    s.new_loan_rate as scb_new_loan_rate,
    s.outstanding_rate as scb_outstanding_rate,
    case
        when l.period_years <= 1.0 then m.policy_rate
        when l.period_years <= 2.0 then m.mortbond_2y
        else m.mortbond_5y
    end as funding_cost,
    case
        when l.period_years <= 1.0 then 'policy_rate'
        when l.period_years <= 2.0 then 'mortbond_2y'
        else 'mortbond_5y'
    end as funding_cost_source,
    round(
        l.list_rate - case
            when l.period_years <= 1.0 then m.policy_rate
            when l.period_years <= 2.0 then m.mortbond_2y
            else m.mortbond_5y
        end,
        4
    ) as gross_margin_listed,
    round(
        s.new_loan_rate - case
            when l.period_years <= 1.0 then m.policy_rate
            when l.period_years <= 2.0 then m.mortbond_2y
            else m.mortbond_5y
        end,
        4
    ) as effective_margin_new,
    round(l.list_rate - s.new_loan_rate, 4) as list_vs_mkt_discount,
    m.funding_date,
    s.scb_period_month
from latest_listed l
cross join latest_market m
left join latest_scb s
    on s.period_label = case
        when l.period_years = 0.25 then '3M'
        when l.period_years = 1.0 then '1Y'
        when l.period_years = 2.0 then '2Y'
        when l.period_years >= 3.0 and l.period_years <= 5.0 then '3-5Y'
        when l.period_years > 5.0 then '5Y+'
    end
order by l.bank, l.period_years
