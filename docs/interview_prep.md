# Nestlé NHS Global Data — Interview Preparation Guide

> **Role:** Senior Data Scientist · NHS Global Data · Barcelona IT Hub
> **Focus:** Statistical Modelling, MLOps, Price Elasticity, MMM, Experimentation

---

## 1. PROJECT NARRATIVE (1-Minute Pitch)

> *"I built a full end-to-end analytics solution simulating Nestlé's FMCG pricing and marketing analytics stack.
> It covers five product categories across five European markets over two years of synthetic data.
> The deliverables include SQL analytical queries, Python-based price elasticity and MMM models,
> and a Streamlit dashboard with Nestlé branding — all designed to demonstrate the exact skill set
> your team needs: causal inference, channel attribution, segmentation, and scenario simulation."*

---

## 2. TECHNICAL DEEP-DIVES

### 2.1 Price Elasticity

**What the interviewer may ask:**
- *"How did you estimate price elasticity?"*
- *"What's the difference between own-price and cross-price elasticity?"*
- *"How would you validate the model?"*

**Your answer framework (STAR):**

| | |
|---|---|
| **Model** | Log-log OLS regression: `ln(Volume) = α + β·ln(Price) + γ·Promo + δ·Trend + ε`. The coefficient β is the price elasticity estimate. |
| **Why log-log?** | Gives a direct elasticity interpretation; handles multiplicative relationships common in demand models. |
| **Endogeneity** | Prices are often endogenous (higher demand → higher prices). In production I'd use Instrumental Variables (IV) — e.g., cost-side instruments (commodity prices) — or a Diff-in-Diff design from a price experiment. |
| **Cross-elasticity** | `∂ln(Q_Nestlé) / ∂ln(P_competitor)`. Estimated by including competitor price in the same regression. Positive cross-elasticity = substitute goods. |
| **Validation** | Hold-out test set (last 13 weeks), MAPE, directional accuracy, residual diagnostics (Breusch-Pagan for heteroskedasticity). |
| **In the dashboard** | Elasticity curve and scenario simulator in Page 2 & Page 6. |

**Key numbers to quote from your project:**
- Coffee (inelastic): ε ≈ −0.9 to −1.5 → premium pricing defensible
- Water / Chocolate (elastic): ε ≈ −1.8 to −2.5 → promotional volume uplift is high but margin-dilutive

---

### 2.2 Marketing Mix Modelling (MMM)

**What the interviewer may ask:**
- *"Walk me through your MMM approach."*
- *"What is adstock and why does it matter?"*
- *"How do you handle multicollinearity in MMM?"*

**Your answer:**

| Concept | Explanation |
|---|---|
| **Adstock** | Models the carryover / lagged effect of advertising. Geometric decay: `X_t = x_t + θ · X_{t-1}`. θ ∈ [0,1]; higher θ = longer carryover. TV typically has θ ≈ 0.35–0.50, Digital θ ≈ 0.10–0.20. |
| **Hill saturation** | `f(x) = x^n / (k^n + x^n)`. Models diminishing returns on spend. k = inflection point; n = shape. Prevents linear extrapolation of ROI at high spend levels. |
| **Multicollinearity** | Channels are often correlated (campaigns run together). Solutions: Ridge regression, Bayesian priors (Robyn/LightweightMMM), sequential testing. |
| **Base vs incremental** | Base = volume sold without any marketing. Incremental = lift attributable to each channel. Dashboard Page 3 shows the stacked area decomposition. |
| **Budget optimisation** | Equalise marginal ROI across channels at the optimal budget point. Implemented via SciPy `minimize` with SLSQP — shown in the Scenario Simulator. |

**Quote from your model:**
- Digital consistently shows the highest ROI (~5.2x) vs TV (~3.8x), suggesting reallocation opportunity.
- Diminishing returns are visible in the spend-vs-revenue scatter at high spend levels.

---

### 2.3 Experimentation & Causal Inference

**What the interviewer may ask:**
- *"How do you design an A/B test for price elasticity?"*
- *"What sample size do you need?"*
- *"How do you handle SUTVA / spillover effects?"*

**Your answer:**

| Topic | Detail |
|---|---|
| **A/B test design** | Randomly assign stores / digital users to control (regular price) and treatment (test price). Block randomisation by market and channel to ensure balance. |
| **Sample size** | `n = 2·(z_α/2 + z_β)² · σ² / δ²`. For 80% power, 5% significance, 10% MDE: typically 5,000–10,000 observations per arm. |
| **Metrics** | Primary: conversion rate / volume lift. Secondary: revenue per unit, margin. Guardrail: brand equity (NPS), cannibalization. |
| **SUTVA** | Stable Unit Treatment Value Assumption — critical in FMCG where in-store promotions can cause store-level spillover. Solution: use store-level (not product-level) randomisation, or geo-level experiments. |
| **Causal inference alternative** | Difference-in-Differences (DiD) when full randomisation isn't possible. Synthetic Control for single-market tests. |
| **Statistical tests** | Two-sample z-test for proportions; Welch t-test for continuous outcomes; Mann-Whitney U if non-normal. |

---

### 2.4 Segmentation

**What the interviewer may ask:**
- *"Why K-Means? What are the limitations?"*
- *"How did you choose k?"*
- *"How would you use segmentation for commercial decisions?"*

**Your answer:**

| Topic | Detail |
|---|---|
| **K-Means** | Simple, scalable, interpretable. Limitation: assumes spherical clusters, sensitive to outliers and scale. Always standardise features first. |
| **Optimal k** | Elbow method (inertia) + Silhouette score. In the project k=5 was selected, aligning with the intuitive FMCG segments. |
| **Alternatives** | DBSCAN (density-based, handles irregular shapes), Gaussian Mixture Models (soft assignment), Hierarchical clustering (dendrogram for visual exploration). |
| **Commercial use** | Target "Budget Conscious" with volume packs; "Premium Seekers" with new product launches; "Family Shoppers" with bundle deals. |
| **Churn model** | Logistic regression / XGBoost on churn_risk_score. Features: recency, frequency, NPS, promo sensitivity. Output: prioritisation for retention campaigns. |

---

## 3. SQL COMPETENCY — QUESTIONS & ANSWERS

### Q: "What's the difference between ROW_NUMBER(), RANK() and DENSE_RANK()?"

```sql
-- Given: scores [100, 100, 90, 80]
ROW_NUMBER():  1, 2, 3, 4  -- always unique
RANK():        1, 1, 3, 4  -- ties get same rank; next rank skipped
DENSE_RANK():  1, 1, 2, 3  -- ties get same rank; next rank NOT skipped
```

### Q: "Write a query to compute a 4-week moving average of revenue."

```sql
SELECT week, brand, market,
       SUM(revenue_eur) AS weekly_revenue,
       AVG(SUM(revenue_eur)) OVER (
           PARTITION BY brand, market
           ORDER BY week
           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
       ) AS revenue_ma4w
FROM sales_data
GROUP BY week, brand, market;
```

### Q: "How would you detect anomalies in weekly sales?"

```sql
WITH stats AS (
    SELECT brand, market,
           AVG(revenue_eur) AS mu,
           STDDEV(revenue_eur) AS sigma
    FROM sales_data
    GROUP BY brand, market
)
SELECT s.week, s.brand, s.market, s.revenue_eur,
       ROUND((s.revenue_eur - st.mu) / st.sigma, 2) AS z_score
FROM sales_data s
JOIN stats st USING (brand, market)
WHERE ABS((s.revenue_eur - st.mu) / st.sigma) > 3;  -- 3-sigma rule
```

### Q: "What's a CTE vs a subquery? When would you use each?"

| | CTE | Subquery |
|---|---|---|
| **Readability** | High — named, modular | Can be harder to follow |
| **Reuse** | Can reference same CTE multiple times | Must repeat subquery |
| **Performance** | May materialise (Postgres) | Usually inlined |
| **Recursive** | Supported (for hierarchical data) | Not supported |

---

## 4. ML / MLOPS QUESTIONS

### Q: "How would you deploy this elasticity model to production?"

**Deployment pipeline:**
1. **Feature Store** (e.g., Feast / AWS SageMaker): precompute weekly aggregated price, volume, promo features.
2. **Model Registry** (MLflow): version, tag, and promote the trained elasticity model.
3. **Batch scoring**: weekly Airflow DAG triggers model.predict() → writes to data warehouse.
4. **Monitoring**: track MAPE drift weekly; trigger retraining if MAPE > threshold (e.g., 10%).
5. **CI/CD**: GitHub Actions runs unit tests + integration tests on every PR before merge.

### Q: "What metrics would you monitor post-deployment?"

| Metric | Why |
|---|---|
| MAPE on hold-out | Model accuracy vs actuals |
| Feature drift (PSI) | Input distribution shift (e.g., competitor pricing changes) |
| Prediction distribution | Output distribution stability |
| Business KPI | Revenue vs forecast — ultimate validation |

---

## 5. BEHAVIOURAL QUESTIONS (STAR FORMAT)

### Q: "Tell me about a time you influenced a business decision with data."

> **Situation:** A commercial team wanted to apply a uniform -15% price reduction across the coffee portfolio to gain market share.
> **Task:** Assess the net revenue impact before the decision was made.
> **Action:** Ran the log-log elasticity model; found that Nescafé Gold had elasticity of -0.9 (inelastic) while Nescafé Classic was -2.1 (elastic). A uniform price cut would destroy margin on Gold unnecessarily.
> **Result:** Recommended a tiered approach: -5% on Gold, -18% on Classic. Projected net revenue: +3.2% vs -7.1% from the blanket cut.

### Q: "How do you explain a complex model to non-technical stakeholders?"

> "I use the 'So what?' chain: *What did the model do? → What did it find? → What should we do about it?*
> For the MMM I showed the stacked area chart — stakeholders immediately understood that 58% of revenue is base (no marketing needed), and that Digital generates 5x ROI vs 3.8x for TV.
> The scenario simulator lets them run their own what-ifs — which builds trust and ownership."

### Q: "How do you handle ambiguity in business requirements?"

> "I align on the decision first: *What action will this analysis unlock?* Then I work backwards to the minimum viable analysis needed to support that decision confidently. I also flag assumptions early and document them — so that when the data doesn't perfectly match reality, stakeholders understand why."

---

## 6. QUESTIONS TO ASK THE INTERVIEWER

1. How does the NHS Global Data team interact with local market teams — is it a centre-of-excellence model or embedded?
2. What is the current state of MLOps maturity — do you use a model registry, or is deployment more manual?
3. Which is more strategically important right now: marketing attribution or pricing analytics?
4. How does the team balance project delivery with building reusable, scalable data products?
5. What does success look like in the first 90 days for someone in this role?

---

## 7. NESTLÉ COMPANY CONTEXT — KEY FACTS

| Fact | Detail |
|---|---|
| Size | ~275,000 employees, 185+ countries, CHF 94.4B revenue (2023) |
| Portfolio | 2,000+ brands across food, beverage, health science |
| Strategy | Nutrition, Health and Wellness; Portfolio Optimisation; eCommerce acceleration |
| IT Hub Barcelona | One of Nestlé's global IT centres; serves NHS (Nestlé Health Science) and other business units |
| Key competitors | Unilever, P&G, Danone, Mars, Ferrero, private label |
| Data tools mentioned | Python, SQL, Power BI; cloud (likely Azure given Microsoft partnership) |
| SRM / Pricing | Strategic Revenue Management — Nestlé has a dedicated SRM function focused on price-pack architecture, mix management, and elasticity |

---

## 8. TECHNICAL STACK SUMMARY (for your CV / interview)

```
Languages:    Python (pandas, numpy, scikit-learn, statsmodels, scipy, streamlit, plotly)
              SQL (PostgreSQL, compatible with BigQuery / Snowflake)
ML Methods:   OLS / Log-log regression, K-Means, PCA, Logistic Regression
Analytics:    Price Elasticity, Marketing Mix Modelling (Adstock + Hill saturation)
              A/B Testing, RFM Segmentation, CLV modelling
MLOps:        Model versioning, feature engineering, batch scoring pipeline design
Visualisation: Streamlit, Plotly, Power BI (conceptual)
Cloud:        Azure / AWS / GCP compatible architectures described
```
