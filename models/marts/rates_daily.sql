-- Daily Swedish rates with one row per date and all series as columns.
-- Also computes covered-bond spreads over equivalent government bonds.

with base as (
    select *
    from {{ ref('stg_se_rates') }}
),

pivoted as (
    select
        rate_date,
        max(case when series_id = 'SECBREPOEFF' then value end) as policy_rate,
        max(case when series_id = 'SECBDEPOEFF' then value end) as deposit_rate,
        max(case when series_id = 'SECBLENDEFF' then value end) as lending_rate,
        max(case when series_id = 'SEDP3MSTIBORDELAYC' then value end) as stibor_3m,
        max(case when series_id = 'SETB3MBENCH' then value end) as tbill_3m,
        max(case when series_id = 'SEGVB2YC' then value end) as govbond_2y,
        max(case when series_id = 'SEGVB5YC' then value end) as govbond_5y,
        max(case when series_id = 'SEGVB10YC' then value end) as govbond_10y,
        max(case when series_id = 'SEMB2YCACOMB' then value end) as mortbond_2y,
        max(case when series_id = 'SEMB5YCACOMB' then value end) as mortbond_5y,
        max(case when series_id = 'SWESTRAVG3M' then value end) as swestr_3m_avg
    from base
    group by rate_date
)

select
    rate_date,
    policy_rate,
    deposit_rate,
    lending_rate,
    stibor_3m,
    tbill_3m,
    govbond_2y,
    govbond_5y,
    govbond_10y,
    mortbond_2y,
    mortbond_5y,
    swestr_3m_avg,
    round(stibor_3m - policy_rate, 4) as stibor_policy_spread_3m,
    round(swestr_3m_avg - policy_rate, 4) as swestr_policy_spread_3m,
    round(mortbond_2y - govbond_2y, 4) as spread_2y,
    round(mortbond_5y - govbond_5y, 4) as spread_5y
from pivoted
order by rate_date desc
