# Funding Proxy Notes

This project uses Swedish mortgage-bond market rates as a transparent proxy for
secured mortgage funding costs. The proxy is useful for public analysis, but it
is not the same thing as a bank's internal transfer price or the marginal cost
of funding a specific customer mortgage.

## Source Series

The covered-bond inputs come from Riksbanken's SWEA API:

- `SEMB2YCACOMB`: Swedish Mortgage Bond, maturity 2 years
- `SEMB5YCACOMB`: Swedish Mortgage Bond, maturity 5 years

Riksbanken groups these under Swedish mortgage bonds (`SE MB`) and its API
metadata identifies the source as Refinitiv. Riksbanken's explanatory page for
Swedish market rates says the mortgage-bond series presented on the website is
Stadshypotek's mortgage bond, `CAISSE`.

`CAISSE` should be treated as a market benchmark label, not as proof that the
Riksbanken series is a transaction-weighted cash-bond yield. Nasdaq's derivatives
quotation lists include fixed-income derivative contract bases named `STH2Y` and
`STH5Y`, described as 2-year and 5-year Caisse- or Stadshypotek bonds. Older
market documentation also refers to Caisse futures. This means the CAISSE name
is connected to both Stadshypotek mortgage-bond benchmarks and listed derivatives
on those benchmark tenors.

Stadshypotek AB is Handelsbanken's mortgage institution and a wholly owned
subsidiary of Handelsbanken. It issues covered bonds under a licence from
Finansinspektionen.

## Why This Series?

The public documentation does not explicitly say why Riksbanken chose this
Stadshypotek/CAISSE series instead of publishing issuer-specific covered-bond
curves for all major banks.

The likely reason is historical benchmark status:

- Riksbanken publishes a selection of Swedish market rates, not a complete
  issuer-level security master.
- Stadshypotek/CAISSE has a long history as a Swedish mortgage-bond benchmark.
- A 1994 Riksdag document describes Stadshypotek benchmark loans as large,
  liquid loans where market makers quoted two-way prices.
- The same document describes OM-cleared Caisse futures for 2-year and 5-year
  bonds.
- Nasdaq's current derivatives quotation list still includes `STH2Y` and
  `STH5Y` fixed-income derivative contract bases, described as 2-year and
  5-year Caisse- or Stadshypotek bonds.
- Riksbanken's current explanatory page still describes the mortgage-bond
  series as Stadshypotek's mortgage bond, `CAISSE`.

Treat this as a documented inference, not a statement from Riksbanken about its
selection policy.

## Other Bank Series

Riksbanken's public SWEA API lists only the two Swedish mortgage-bond series
above. It does not list separate public API series for Swedbank Hypotek, Nordea
Hypotek, SEB, SBAB/SCBC, Länsförsäkringar Hypotek, Danske Hypotek, or other
covered-bond issuers.

Issuer-level covered-bond market data does exist elsewhere:

- Riksbank economic commentaries use rates on benchmark covered bonds from the
  seven largest covered-bond institutions: Danske Bank, Nordea, SEB, Swedbank,
  Länsförsäkringar, SBAB, and Handelsbanken/Stadshypotek. Those charts cite
  Bloomberg, Macrobond, and Riksbanken, not the public SWEA API.
- Issuer investor-relations pages publish benchmark-bond programmes and
  outstanding benchmark bonds. For example, Swedbank publishes SEK benchmark
  covered bonds with loan numbers, ISINs, coupon, maturity, and outstanding
  nominal volume, but not a daily yield time series.
- Nordea and SBAB publish covered-bond programme pages and documentation. These
  are useful for identifying issuer, programme, and benchmark-bond universe, but
  they are not directly comparable to the Riksbanken `SEMB*` daily yield series.
- Nasdaq lists individual Swedish mortgage bonds, including Stadshypotek,
  Nordea Hypotek, SEB/SCBC, and other issuer instruments. These pages expose
  bond pages, historical prices/trades, and MiFIR trade-report links, but not a
  simple public Riksbank-style 2Y/5Y issuer curve.
- Nasdaq also lists Swedish mortgage-bond futures for Swedbank Hypotek,
  Stadshypotek, and Nordea Hypotek. These futures are useful evidence that
  issuer-specific benchmark markets exist, but they are derivatives contracts,
  not the same object as the Riksbanken `SE MB` spot-yield series.
- Nasdaq OMRX mortgage-bond indexes provide broader mortgage-bond index context,
  but index access and methodology are separate from the Riksbanken SWEA series.

If this project needs issuer-specific funding curves, likely next data-source
options are Bloomberg/Refinitiv, Nasdaq fixed-income pages and trade reports,
issuer benchmark-bond lists from investor-relations pages, Covered Bond Label
data, or a vendor/API with historical bond prices and yields.

Working classification of public alternatives:

| Source | Competitor coverage | Shape | Fit for dbt |
| --- | --- | --- | --- |
| Riksbanken SWEA | Stadshypotek/CAISSE only for mortgage bonds | Daily 2Y/5Y market-rate series | Current source |
| Riksbank research PDFs | Seven large issuers in selected charts | Published chart/table, sources Bloomberg/Macrobond | Good evidence, not a stable feed |
| Issuer IR pages | Swedbank, Nordea, SBAB/SCBC, Handelsbanken, others | Benchmark bond lists, ISINs, final terms, outstanding volumes | Good security master input |
| Nasdaq mortgage-bond pages | Many individual issuer bonds | Per-security pages with historical prices/trades links | Possible scrape/API candidate |
| Nasdaq mortgage-bond futures | Swedbank Hypotek, Stadshypotek, Nordea Hypotek | Derivative prices/fixes for standardized futures | Useful market signal, not spot curve |
| Nasdaq OMRX mortgage indexes | Broad mortgage-bond index context | Index level and index families | Useful context, not issuer curve |

## Paths Forward and Cost

Main conclusion: bank-specific funding proxies are now a data-sourcing problem,
not a Riksbanken API problem. Riksbanken's public API does not appear to provide
competitor-specific 2Y/5Y covered-bond curves. The realistic paths are:

| Path | Cash cost | Engineering cost | What it supports | Main limitation |
| --- | --- | --- | --- | --- |
| Keep Riksbanken CAISSE proxy | 0 incremental data cost | None beyond current pipeline | Public Swedish mortgage-bond market proxy | Not bank-specific; Stadshypotek/Handelsbanken-linked |
| Vendor data: Bloomberg, LSEG/Refinitiv, Macrobond | Quote-based; Bloomberg Terminal estimates from non-official sources are often in the tens of thousands of USD per seat per year; enterprise/API data can be materially higher | 1-2 weeks after access for ingestion, mapping, tests, and app contract changes | Cleanest path to issuer-level bond prices, yields, curves, and history | Procurement, licence restrictions, redistribution limits |
| Official Nasdaq Nordic Fixed Income data | Nasdaq's 2026 price list includes Nordic Fixed Income professional distribution at EUR 3,506/month, Nordic Fixed Income Basic Data enterprise licence at EUR 3,338/month for trading members, Nordic Fixed Income non-display trading use at EUR 408/month, Nordic Fixed Income derived-data licence at EUR 591/month, Nordic delayed redistribution at EUR 909/month, and Nordic delayed website publication at EUR 544/month; exact required bundle depends on use case and contract | 2-4+ weeks for production curve construction | Exchange/market-data source for individual listed bonds, pre/post-trade data, reference data, and derived curves | Licensing complexity; still need yield calculation, benchmark selection, interpolation, stale-data handling |
| Nasdaq official Swedish bond price-list PDFs | Nasdaq's other-data price lists describe a paid Nordic Official Price List Document product at EUR 500/year, including "Official Pricelist Fixed Income Swedish Bonds" produced daily as PDF | 2-5 days to obtain a sample, parse fields, and test coverage; longer if productionized | Potential low-cost source for listed Swedish bond price observations and instrument metadata | Need sample access; for internal use only; likely a human-readable report rather than the best production interface |
| Nasdaq Fixed Income reference and end-of-day files | Nasdaq lists Nordic Fixed Income Reference Data files at EUR 236/month and Nordic Fixed Income End-of-day files at EUR 496/month in the April 2026 other-data price list; both are available through File Delivery Service / Nasdaq Data Link files | 1-2 weeks for ingestion, issuer mapping, YTM calculation, and monitoring | More production-shaped source for security master plus daily trade/listing/order-book data | Still requires licence review, yield construction, stale-data handling, and issuer curve methodology |
| Nasdaq Fixed Income Bond Analytics | Nasdaq's April 2026 other-data price list shows Nordic Fixed Income Bond Analytics at EUR 1,165/month, or EUR 1,442/month with fair value intraday; the licence note says it includes unlimited internal use, display use, creation of derived data, and non-display use in internal applications | 1-2 weeks after access if fields include usable covered-bond analytics | Potentially avoids doing all bond analytics ourselves | Need sample file/field list; internal-use rights do not automatically imply public redistribution rights |
| Nasdaq delayed trade-report/public pages prototype | 0 direct data fee if only manually inspecting or building an internal proof of concept from public delayed files/pages | 2-5 days for a proof of concept; 2-4+ weeks to harden | Tests whether public Nasdaq data is dense enough to build issuer curves | Fragile, limited retention, licence/terms need review before production or redistribution |
| Issuer IR pages plus bond math | 0 direct data fee | 2-5 days to build a security master; ongoing maintenance | Identifies issuer benchmark bonds, ISINs, coupons, maturities, outstanding volume | Not enough alone: issuer pages usually do not provide daily secondary-market yields |
| Covered Bond Label / ECBC data | Usually useful as public/reference data subject to terms of use | 2-5 days to evaluate and ingest relevant templates | Cover-pool and programme transparency, issuer context | Not a daily market-yield source |
| Model-only issuer adjustment | 0 direct data fee | 2-5 days for a transparent approximation | Scenario analysis when issuer curves are unavailable | Should not be described as observed bank-specific funding |

Recommendation:

1. Keep the current CAISSE proxy in the dashboard, but label it conservatively as
   a Swedish mortgage-bond market proxy.
2. Run a short Nasdaq/issuer proof of concept for Stadshypotek, Swedbank
   Hypotek, Nordea Hypotek, and SCBC/SBAB. The test should answer whether we can
   reliably identify benchmark bonds, obtain enough daily prices or quotes, and
   compute stable 2Y/5Y yields. Ask Nasdaq for sample files for:
   - Official Pricelist Fixed Income Swedish Bonds PDF
   - Nordic Fixed Income Reference Data files
   - Nordic Fixed Income End-of-day files
   - Nordic Fixed Income Bond Analytics, including fair value fields if
     available
3. If the proof of concept fails on data density, reproducibility, or licensing,
   use Bloomberg/LSEG/Macrobond for production bank-specific curves, or avoid
   bank-specific funding claims.

The minimum production work for a self-built curve is larger than ingestion:
maintain a bond security master, map issuers to banks, calculate clean/dirty
prices and yields, select or weight benchmark bonds, interpolate to 2Y and 5Y,
flag stale observations, monitor source changes, and document the licence basis
for any derived data displayed in the app.

The current best Nasdaq path is probably not PDF parsing as a production
strategy. The official Swedish bond price-list PDF may be useful as a cheap
sample or audit artifact, but Nasdaq's structured file products are a better fit
for a dbt pipeline:

- Fixed Income Reference Data files provide ISIN, ticker, bond type, rate
  calculation type, day count method, maturity date, maturity value, and coupon
  rate.
- Fixed Income End-of-day files provide daily trade reports with trade details,
  listing information, and order-book information.
- Fixed Income Bond Analytics may provide calculated analytics/fair-value data
  that reduces our own bond-math burden.

Before building anything, request sample files and licence answers for:

- whether Swedish covered bonds are included with enough fields to identify
  issuer, instrument, coupon, maturity, price, yield, and volume;
- whether historical backfill is available beyond the previous 30 days;
- whether derived 2Y/5Y issuer curves can be stored and shown publicly in this
  dashboard;
- whether public display requires the derived-data licence, delayed website
  publication licence, or a separate redistribution agreement.

## Is CAISSE Based on Actual Trades?

The public sources found so far do not say that CAISSE is a transaction-based
rate. That distinction matters: Riksbanken explicitly describes SWESTR as a
transaction-based reference rate, but does not use that language for the
mortgage-bond series.

The better interpretation is quote-driven market data:

- Swedish covered bonds are usually registered at Nasdaq Stockholm, but actual
  bond trading is primarily over the counter.
- Covered-bond market makers display indicative two-way prices in electronic
  information systems, relayed by Reuters/Refinitiv.
- Firm prices are quoted on request, and many secondary-market deals are
  concluded by phone.

So these series should be described as observable market-rate/yield series from
Refinitiv/Riksbanken, not as pure reported-trade averages. The public
documentation found so far is also not enough to say whether the Riksbanken
`CAISSE` rates are calculated directly from cash-bond quotes, futures-implied
levels, or a Refinitiv benchmark methodology that blends observable inputs.

## Modeling Use

The `rates_daily` mart pivots the Riksbanken series into `mortbond_2y` and
`mortbond_5y`, then derives:

- `spread_2y = mortbond_2y - govbond_2y`
- `spread_5y = mortbond_5y - govbond_5y`

The bank margin marts use those spreads as a covered-bond funding proxy. This is
a modeling assumption:

- It captures the observable market price of Swedish mortgage-bond funding.
- It is anchored to Stadshypotek/Handelsbanken-linked CAISSE series rather than
  a broad all-bank funding composite.
- It does not reveal any individual bank's actual funding mix, hedge book,
  deposit funding share, liquidity buffer cost, capital cost, or internal
  transfer-pricing curve.

Preferred wording in product copy and docs:

> Swedish mortgage-bond market proxy, based on Riksbanken/Refinitiv
> Stadshypotek/CAISSE benchmark series.

Avoid stronger wording such as:

> The bank's actual funding cost.

## Source Links

- Riksbanken, Swedish market rates:
  https://www.riksbank.se/en-gb/statistics/interest-rates-and-exchange-rates/explanations--interest-rates-and-exchange-rates/swedish-market-rates/
- Riksbanken, series for the API:
  https://www.riksbank.se/en-gb/statistics/interest-rates-and-exchange-rates/retrieving-interest-rates-and-exchange-rates-via-api/series-for-the-api/
- Riksdag, Stadshypotek benchmark and Caisse futures history:
  https://www.riksdagen.se/sv/dokument-och-lagar/dokument/proposition/andring-i-lagen-1992701-om-konungariket_gi0382/
- Riksbanken, covered-bond purchases and issuer-level benchmark bond rates:
  https://www.riksbank.se/globalassets/media/rapporter/ekonomiska-kommentarer/engelska/2022/the-riksbanks-purchases-of-covered-bonds-and-the-impact-on-mortgage-rates.pdf
- Riksbanken, covered-bond risk premiums and benchmark-bond issuers:
  https://www.riksbank.se/globalassets/media/rapporter/ekonomiska-kommentarer/engelska/2021/the-development-of-risk-premiums-on-covered-bonds-during-the-coronavirus-pandemic.pdf
- Association of Swedish Covered Bond issuers, market information:
  https://www.ascb.se/market-information/
- Swedbank, covered bonds:
  https://www.swedbank.com/investor-relations/debt-investors/debt-issues/covered-bonds.html
- Nordea, bonds:
  https://www.nordea.com/en/investors/bonds
- SBAB/SCBC, covered-bond funding:
  https://www.sbab.se/1/in_english/investor_relations/investor_relations/the_sbab_groups_funding_programmes/scbc_-_covered_bond_funding.html
- Nasdaq Nordic fixed-income derivatives:
  https://www.nasdaq.com/solutions/fixed-income-derivatives-clearing
- Nasdaq derivatives quotation list, `STH2Y` and `STH5Y` Caisse/Stadshypotek
  contract bases:
  https://www.nasdaq.com/docs/2026/04/13/260413_App_01_-_Quotation_List_0.pdf
- Nasdaq market-data catalogue:
  https://www.nasdaq.com/solutions/data/market-data-catalog
- Nasdaq European Markets Data Price List, April 2026:
  https://www.nasdaq.com/docs/Nasdaq_European_Exchange_Market_Data_Price_List_April_2026_REDLINE.pdf
- Nasdaq other data products price list, official Nordic price-list documents:
  https://www.nasdaq.com/docs/other-data-products-price-list-january-2025-redline
- Nasdaq European Market Other Data Products Price List, April 2026:
  https://www.nasdaq.com/docs/Nasdaq_European_Market_Other_Data_Products_Price_List_April_2026
- Nasdaq Nordic Reference Data Files:
  https://www.nasdaq.com/solutions/data/nasdaq-nordic-reference-data-files
- Nasdaq Data News Europe 2026-06, FDS migration to Nasdaq Data Link Files:
  https://view.news.eu.nasdaq.com/view?id=b8cce52d889b395d9030aa9b4d07a929a&lang=en&src=rss
- Nasdaq Nordic Fixed Income delayed pre-trade reports:
  https://tradereports.nasdaq.com/bonds/trade-reports/pre-trade
- Nasdaq OMRX Mortgage Bond Index:
  https://indexes.nasdaq.com/Index/Overview/OMRXMORT
- Handelsbanken, funding:
  https://www.handelsbanken.com/en/investor-relations/debt-investors/funding
- Handelsbanken, subsidiaries:
  https://www.handelsbanken.com/en/about-the-group/organisation/subsidiaries
- Bloomberg Data License:
  https://www.bloomberg.com/professional/products/data/data-management/data-license/
- LSEG Workspace for fixed income:
  https://www.lseg.com/en/data-analytics/products/workspace/fixed-income
- Macrobond Data:
  https://www.macrobond.com/platform/data
- Covered Bond Label data:
  https://coveredbondlabel.com/bonds
