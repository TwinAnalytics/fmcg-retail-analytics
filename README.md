# Nestlé NHS Global Data — Analytics Project

**Senior Data Scientist Demo · Barcelona IT Hub · 2024**

An end-to-end FMCG analytics solution demonstrating price elasticity,
marketing mix modelling, customer segmentation, and A/B experimentation —
built with Nestlé brand style and interactive Streamlit dashboard.

---

## Quick Start

```bash
pip install -r requirements.txt
python data/generate_data.py
streamlit run dashboard/app.py
```

## Structure

| Path | Description |
|---|---|
| `data/generate_data.py` | Synthetic data generator — run first |
| `sql/analysis_queries.sql` | 15+ production SQL queries |
| `models/price_elasticity.py` | Log-log OLS elasticity model |
| `models/mmm_model.py` | Adstock + Hill saturation MMM |
| `models/segmentation.py` | K-Means + RFM segmentation |
| `dashboard/app.py` | Streamlit dashboard (6 pages) |
| `docs/interview_prep.md` | Technical Q&A and STAR answers |
| `docs/project_overview.md` | Full architecture and dataset reference |

## Dashboard Preview

| Page | Key Visual |
|---|---|
| Executive Overview | KPI cards, revenue trend, channel mix, margin heatmap |
| Price Elasticity | Box plots, promo uplift, competitor price tracker |
| Marketing Mix (MMM) | Stacked area attribution, channel ROI, diminishing returns |
| Customer Segmentation | Segment profiles, CLV vs churn risk, RFM scatter |
| Experimentation | A/B significance waterfall, lift vs p-value |
| Scenario Simulator | Price elasticity curves, budget reallocation tool |

---

*Synthetic data only — no proprietary Nestlé information used.*
