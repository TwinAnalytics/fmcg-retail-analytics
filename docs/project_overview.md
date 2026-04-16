# Project Overview — Nestlé NHS Global Data Analytics Dashboard

## Purpose

This project simulates a realistic FMCG data science workstream covering:
- Price elasticity estimation and scenario planning
- Marketing Mix Modelling (MMM) with channel attribution
- Customer segmentation and lifetime value (CLV)
- A/B experimentation with causal inference
- Interactive Streamlit dashboard with Nestlé branding

---

## Architecture

```
nestle_analytics_project/
│
├── data/
│   ├── generate_data.py          # Synthetic dataset generator (run first)
│   ├── sales_data.csv            # Weekly sales: brand × market × channel
│   ├── marketing_spend.csv       # Weekly spend: 6 marketing channels
│   ├── customer_data.csv         # 8,000 synthetic customers with attributes
│   ├── competitor_prices.csv     # Weekly competitor price index
│   ├── experiments.csv           # 10 A/B test records with statistics
│   └── mmm_contributions.csv     # Pre-computed MMM contribution table
│
├── sql/
│   └── analysis_queries.sql      # 15+ production-grade SQL queries
│
├── models/
│   ├── price_elasticity.py       # Log-log OLS elasticity model + scenario sim
│   ├── mmm_model.py              # Adstock + Hill saturation MMM + budget opt
│   └── segmentation.py           # K-Means + RFM customer segmentation
│
├── dashboard/
│   └── app.py                    # Streamlit multi-page dashboard
│
├── docs/
│   └── project_overview.md       # This file
│
├── requirements.txt
└── README.md
```

---

## Datasets

### sales_data.csv
| Column | Description |
|---|---|
| week | Week start date (Monday) |
| category | Product category (Coffee, Chocolate, Water, Dairy, Baby Food) |
| brand | Brand name (e.g., Nescafé Gold, KitKat) |
| market | Country (Spain, Germany, France, UK, Italy) |
| channel | Trade channel (Modern Trade, E-Commerce, Convenience, Foodservice, Pharmacy) |
| regular_price | Base shelf price (€) |
| price_charged | Actual price (net of promotion) |
| promo_flag | Binary: 1 if on promotion |
| promo_depth_pct | Discount depth (% off regular price) |
| volume_units | Units sold |
| revenue_eur | Gross revenue (€) |
| gross_profit_eur | Revenue minus COGS (€) |
| gross_margin_pct | Gross profit as % of revenue |
| elasticity | Own-price elasticity used in data generation |

**~104,000 rows** (20 brands × 5 markets × 104 weeks)

### marketing_spend.csv
| Column | Description |
|---|---|
| week | Week start date |
| category | Product category |
| market | Country |
| spend_tv | Weekly TV spend (€) |
| spend_digital | Digital advertising spend (€) |
| spend_social_media | Social media spend (€) |
| spend_out_of_home | OOH/DOOH spend (€) |
| spend_print | Print spend (€) |
| spend_sponsorship | Sponsorship/events spend (€) |
| total_marketing_spend | Sum of all channels (€) |
| grp_tv | Gross Rating Points (TV) |
| impressions_digital | Estimated digital impressions |

**~5,200 rows** (5 categories × 5 markets × 104 weeks)

### customer_data.csv
8,000 synthetic customers with: segment, market, age, tenure,
monthly spend, visit frequency, brand loyalty, promo sensitivity,
preferred category/channel, digital activity, NPS, churn risk, CLV.

### competitor_prices.csv
Weekly competitor price for 3 competitors per category per market.
Includes price index (competitor price / Nestlé regular price × 100).

### experiments.csv
10 A/B test records across categories and markets.
Includes: control/treatment sizes, conversion rates, lift, z-score, p-value,
statistical significance flag, incremental revenue.

### mmm_contributions.csv
Pre-computed weekly revenue attribution split:
base | TV | digital | social | promo | seasonal contributions.

---

## Dashboard Pages

| Page | Content |
|---|---|
| 📊 Executive Overview | KPI cards, revenue by category/market, channel mix, margin heatmap |
| 📈 Price Elasticity | Elasticity box plots, promo effectiveness, Nestlé vs competitor price tracker |
| 📺 Marketing Mix (MMM) | Stacked area attribution, channel ROI table, diminishing returns scatter |
| 👥 Customer Segmentation | Segment profiles, CLV analysis, RFM scatter, churn risk |
| 🔬 Experimentation | A/B test results, significance waterfall, lift vs p-value chart |
| 🎯 Scenario Simulator | Price elasticity curves, budget reallocation optimiser |

---

## Models

### Price Elasticity (`models/price_elasticity.py`)
- **Method:** Log-log OLS regression with HC3 robust standard errors
- **Features:** ln(price), promo flag, week trend
- **Output:** Elasticity estimate per brand × market, p-value, R², scenario table

### Marketing Mix Model (`models/mmm_model.py`)
- **Transformations:** Geometric adstock (θ) + Hill saturation (k, n)
- **Regression:** OLS on transformed channel features + seasonal dummies
- **Output:** Revenue contribution decomposition by channel
- **Optimiser:** SciPy SLSQP for budget allocation under diminishing returns

### Customer Segmentation (`models/segmentation.py`)
- **Method:** K-Means clustering (k=5) with StandardScaler
- **Selection:** Elbow method + Silhouette score
- **Enrichment:** RFM scoring (Recency/Frequency/Monetary)
- **Output:** Cluster labels + PCA coordinates for visualisation

---

## SQL Highlights

The `sql/analysis_queries.sql` file contains 6 analytical sections:

1. **Revenue & Volume Performance** — YoY growth, rolling 13-week MA, channel mix
2. **Price Elasticity Analysis** — Price corridors, promo impact, cross-elasticity
3. **Marketing Mix & ROI** — Channel ROI, diminishing returns quartiles, spend intensity
4. **Customer Segmentation** — Segment profile, high-value at-risk list, RFM scoring
5. **Experimentation** — A/B summary, ATE, experiment ROI
6. **Integrated View** — Dashboard base view, category health scorecard

Notable SQL patterns used:
- Window functions: `LAG`, `LEAD`, `RANK`, `NTILE`, `PERCENTILE_CONT`, rolling `AVG`
- CTEs for modular query design
- Self-joins for period comparison
- `CREATE OR REPLACE VIEW` for reusable dashboard base
- `CASE WHEN` for segmentation and classification logic

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic data
python data/generate_data.py

# 3. (Optional) Run models
python models/price_elasticity.py
python models/mmm_model.py
python models/segmentation.py

# 4. Launch dashboard
streamlit run dashboard/app.py
```
