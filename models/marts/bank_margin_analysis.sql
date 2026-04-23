-- Latest bank listed mortgage rates with estimated gross margin over funding cost.

with latest_market as (
    select
        rate_date as funding_date,
        policy_rate,
        mortbond_2y,
        mortbond_5y,
        spread_2y,
        spread_5y
    from {{ ref('rates_daily') }}
    where rate_date = (
        select max(rate_date)
        from {{ ref('rates_daily') }}
        where mortbond_5y is not null
    )
),

latest_listed as (
    select
        scrape_date,
        bank,
        period_label,
        period_years,
        list_rate,
        avg_rate
    from {{ ref('stg_bank_listed_rates') }}
    where scrape_date = (
        select max(scrape_date)
        from {{ ref('stg_bank_listed_rates') }}
    )
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
    l.period_label as period_label_display,
    l.period_years,
    l.list_rate,
    l.avg_rate,
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
    ) as gross_margin,
    case
        when l.avg_rate is not null then round(
            l.avg_rate - case
                when l.period_years <= 1.0 then m.policy_rate
                when l.period_years <= 2.0 then m.mortbond_2y
                else m.mortbond_5y
            end,
            4
        )
    end as avg_margin,
    l.scrape_date,
    m.funding_date
from latest_listed l
cross join latest_market m
order by l.bank, l.period_years

