-- Bank listed rates versus SCB MFI market-average rates and a stylized Swedish
-- mortgage funding stack. Variable-rate buckets are modeled as longer covered
-- bond funding swapped into 3M money-market exposure, while fixed buckets use
-- a covered-bond curve with interpolation between 2Y and 5Y.

with latest_market as (
    select
        rate_date as funding_date,
        policy_rate,
        stibor_3m,
        govbond_2y,
        govbond_5y,
        mortbond_2y,
        mortbond_5y,
        stibor_policy_spread_3m,
        swestr_policy_spread_3m,
        spread_2y,
        spread_5y
    from {{ ref('rates_daily') }}
    where rate_date = (
        select max(rate_date)
        from {{ ref('rates_daily') }}
        where policy_rate is not null
          and govbond_2y is not null
          and govbond_5y is not null
          and swestr_policy_spread_3m is not null
          and spread_2y is not null
          and spread_5y is not null
    )
),

latest_listed as (
    select
        bank,
        period_label as period_label_display,
        period_years,
        list_rate,
        listed_rate_age_days,
        listed_rate_freshness
    from {{ ref('int_latest_bank_listed_rates') }}
),

latest_scb as (
    select
        period_label,
        max(case when loan_type = '0100' then rate end) as new_loan_rate,
        max(case when loan_type = '0200' then rate end) as outstanding_rate,
        max(case when loan_type = '0100' then period_month end) as scb_new_loan_period_month,
        max(case when loan_type = '0200' then period_month end) as scb_outstanding_period_month,
        max(scb_rate_age_days) as scb_rate_age_days,
        case
            when max(case when scb_rate_freshness = 'stale' then 1 else 0 end) = 1 then 'stale'
            when max(case when scb_rate_freshness = 'aging' then 1 else 0 end) = 1 then 'aging'
            else 'fresh'
        end as scb_rate_freshness
    from {{ ref('int_latest_scb_mortgage_rates') }}
    group by period_label
),

funding_components as (
    select
        l.bank,
        l.period_label_display,
        l.period_years,
        l.list_rate,
        l.listed_rate_age_days,
        l.listed_rate_freshness,
        m.funding_date,
        case
            when l.period_years <= 1.0 then 'swapped_covered_bond_variable_proxy'
            when l.period_years < 5.0 then 'interpolated_covered_bond_curve'
            else 'five_year_covered_bond_proxy'
        end as funding_model,
        case
            when l.period_years <= 2.0 then cast(1.0 as double)
            when l.period_years < 5.0 then cast(round((5.0 - l.period_years) / 3.0, 4) as double)
            else cast(0.0 as double)
        end as funding_weight_2y,
        case
            when l.period_years <= 2.0 then cast(0.0 as double)
            when l.period_years < 5.0 then cast(round((l.period_years - 2.0) / 3.0, 4) as double)
            else cast(1.0 as double)
        end as funding_weight_5y,
        case
            when l.period_years <= 1.0 then m.policy_rate
            else cast(0.0 as double)
        end as policy_anchor_component,
        case
            when l.period_years <= 1.0 then coalesce(m.swestr_policy_spread_3m, cast(0.0 as double))
            else cast(0.0 as double)
        end as short_rate_spread_component,
        case
            when l.period_years <= 1.0 then cast(0.0 as double)
            when l.period_years <= 2.0 then m.govbond_2y
            when l.period_years < 5.0 then round(
                ((5.0 - l.period_years) / 3.0) * m.govbond_2y
                + ((l.period_years - 2.0) / 3.0) * m.govbond_5y,
                4
            )
            else m.govbond_5y
        end as risk_free_curve_component,
        case
            when l.period_years <= 1.0 then m.spread_5y
            when l.period_years <= 2.0 then m.spread_2y
            when l.period_years < 5.0 then round(
                ((5.0 - l.period_years) / 3.0) * m.spread_2y
                + ((l.period_years - 2.0) / 3.0) * m.spread_5y,
                4
            )
            else m.spread_5y
        end as covered_bond_spread_component
    from latest_listed l
    cross join latest_market m
)

select
    f.bank,
    case cast(round(f.period_years * 4) as integer)
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
        else lpad(cast(cast(round(f.period_years * 12) as integer) as varchar), 3, '0') || 'M'
    end as period_label,
    f.period_label_display,
    f.period_years,
    case
        when f.period_years = 0.25 then '3M'
        when f.period_years = 1.0 then '1Y'
        when f.period_years = 2.0 then '2Y'
        when f.period_years >= 3.0 and f.period_years <= 5.0 then '3-5Y'
        when f.period_years > 5.0 then '5Y+'
    end as scb_bucket,
    f.list_rate,
    f.listed_rate_age_days,
    f.listed_rate_freshness,
    s.new_loan_rate as scb_new_loan_rate,
    s.outstanding_rate as scb_outstanding_rate,
    s.scb_rate_age_days,
    s.scb_rate_freshness,
    f.funding_model,
    f.funding_weight_2y,
    f.funding_weight_5y,
    f.policy_anchor_component,
    f.short_rate_spread_component,
    f.risk_free_curve_component,
    f.covered_bond_spread_component,
    round(
        f.policy_anchor_component
        + f.short_rate_spread_component
        + f.risk_free_curve_component
        + f.covered_bond_spread_component,
        4
    ) as funding_cost,
    case
        when f.period_years <= 1.0 then 'policy_rate + (swestr_3m_avg - policy_rate) + spread_5y'
        when f.period_years < 5.0 then 'blended govt curve + blended covered spread (2Y to 5Y)'
        else 'govbond_5y + spread_5y'
    end as funding_cost_source,
    round(
        f.list_rate - (
            f.policy_anchor_component
            + f.short_rate_spread_component
            + f.risk_free_curve_component
            + f.covered_bond_spread_component
        ),
        4
    ) as gross_margin_listed,
    round(
        s.new_loan_rate - (
            f.policy_anchor_component
            + f.short_rate_spread_component
            + f.risk_free_curve_component
            + f.covered_bond_spread_component
        ),
        4
    ) as effective_margin_new,
    round(f.list_rate - s.new_loan_rate, 4) as list_vs_mkt_discount,
    f.funding_date,
    coalesce(s.scb_new_loan_period_month, s.scb_outstanding_period_month) as scb_period_month,
    s.scb_new_loan_period_month,
    s.scb_outstanding_period_month
from funding_components f
left join latest_scb s
    on s.period_label = case
        when f.period_years = 0.25 then '3M'
        when f.period_years = 1.0 then '1Y'
        when f.period_years = 2.0 then '2Y'
        when f.period_years >= 3.0 and f.period_years <= 5.0 then '3-5Y'
        when f.period_years > 5.0 then '5Y+'
    end
order by f.bank, f.period_years
