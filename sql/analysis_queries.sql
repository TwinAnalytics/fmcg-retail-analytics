-- =============================================================================
-- Nestlé NHS Global Data Analytics — SQL Analysis Queries
-- =============================================================================
-- Database: PostgreSQL 14+  (also compatible with BigQuery / Snowflake with
--           minor dialect adjustments noted inline)
-- Tables:
--   sales_data         - weekly sales by brand / market / channel
--   marketing_spend    - weekly marketing investment by channel
--   customer_data      - customer-level attributes and segment scores
--   competitor_prices  - weekly competitor price index
--   experiments        - A/B test log
--   mmm_contributions  - pre-computed marketing-mix model contributions
-- =============================================================================


-- =============================================================================
-- SECTION 1: REVENUE & VOLUME PERFORMANCE
-- =============================================================================

-- 1.1  YoY revenue comparison by category
-- -----------------------------------------------------------------------------
SELECT
    category,
    year,
    SUM(revenue_eur)                                               AS total_revenue,
    SUM(volume_units)                                              AS total_volume,
    ROUND(AVG(price_charged)::NUMERIC, 2)                         AS avg_price,
    ROUND(AVG(gross_margin_pct)::NUMERIC, 1)                      AS avg_margin_pct,
    LAG(SUM(revenue_eur)) OVER (PARTITION BY category ORDER BY year) AS prev_year_revenue,
    ROUND(
        (SUM(revenue_eur) - LAG(SUM(revenue_eur)) OVER (PARTITION BY category ORDER BY year))
        / NULLIF(LAG(SUM(revenue_eur)) OVER (PARTITION BY category ORDER BY year), 0) * 100
    , 1)                                                           AS yoy_revenue_growth_pct
FROM sales_data
GROUP BY category, year
ORDER BY category, year;


-- 1.2  Rolling 13-week revenue trend per brand (moving average)
-- -----------------------------------------------------------------------------
SELECT
    week,
    brand,
    market,
    SUM(revenue_eur)                                         AS weekly_revenue,
    ROUND(
        AVG(SUM(revenue_eur)) OVER (
            PARTITION BY brand, market
            ORDER BY week
            ROWS BETWEEN 12 PRECEDING AND CURRENT ROW
        )::NUMERIC, 2)                                       AS revenue_ma13w
FROM sales_data
GROUP BY week, brand, market
ORDER BY brand, market, week;


-- 1.3  Channel mix evolution — quarterly share of revenue
-- -----------------------------------------------------------------------------
SELECT
    quarter,
    year,
    channel,
    SUM(revenue_eur)                                                              AS channel_revenue,
    ROUND(
        SUM(revenue_eur) * 100.0
        / SUM(SUM(revenue_eur)) OVER (PARTITION BY quarter, year)
    , 1)                                                                          AS channel_share_pct
FROM sales_data
GROUP BY quarter, year, channel
ORDER BY year, quarter, channel_share_pct DESC;


-- 1.4  Top 10 brand × market combinations by gross profit
-- -----------------------------------------------------------------------------
SELECT
    brand,
    market,
    SUM(revenue_eur)                       AS total_revenue,
    SUM(gross_profit_eur)                  AS total_gross_profit,
    ROUND(AVG(gross_margin_pct)::NUMERIC, 1) AS avg_margin_pct,
    RANK() OVER (ORDER BY SUM(gross_profit_eur) DESC) AS profit_rank
FROM sales_data
GROUP BY brand, market
ORDER BY total_gross_profit DESC
LIMIT 10;


-- =============================================================================
-- SECTION 2: PRICE ELASTICITY ANALYSIS
-- =============================================================================

-- 2.1  Own-price elasticity estimate per category (log-log regression proxy)
--      Uses the stored elasticity column from model output
-- -----------------------------------------------------------------------------
SELECT
    category,
    brand,
    market,
    ROUND(AVG(elasticity)::NUMERIC, 3)               AS avg_price_elasticity,
    ROUND(STDDEV(elasticity)::NUMERIC, 3)            AS elasticity_std,
    COUNT(*)                                          AS observations,
    CASE
        WHEN AVG(elasticity) < -2.0 THEN 'Highly Elastic'
        WHEN AVG(elasticity) BETWEEN -2.0 AND -1.0 THEN 'Elastic'
        WHEN AVG(elasticity) BETWEEN -1.0 AND -0.5 THEN 'Inelastic'
        ELSE 'Highly Inelastic'
    END                                               AS elasticity_category
FROM sales_data
GROUP BY category, brand, market
ORDER BY avg_price_elasticity;


-- 2.2  Revenue impact of promotional price reductions
--      Compares average revenue per unit in promo vs non-promo weeks
-- -----------------------------------------------------------------------------
SELECT
    category,
    brand,
    promo_flag,
    COUNT(*)                                             AS weeks_count,
    ROUND(AVG(price_charged)::NUMERIC, 2)               AS avg_price,
    ROUND(AVG(volume_units)::NUMERIC, 0)                AS avg_volume,
    ROUND(AVG(revenue_eur)::NUMERIC, 0)                 AS avg_weekly_revenue,
    ROUND(AVG(gross_margin_pct)::NUMERIC, 1)            AS avg_margin_pct,
    ROUND(AVG(promo_depth_pct)::NUMERIC, 1)             AS avg_promo_depth_pct
FROM sales_data
GROUP BY category, brand, promo_flag
ORDER BY category, brand, promo_flag;


-- 2.3  Price corridor analysis — distribution of prices relative to regular
-- -----------------------------------------------------------------------------
SELECT
    category,
    market,
    ROUND(AVG(regular_price)::NUMERIC, 2)                              AS avg_regular_price,
    ROUND(MIN(price_charged)::NUMERIC, 2)                              AS min_price_charged,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price_charged)::NUMERIC, 2) AS p25_price,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price_charged)::NUMERIC, 2) AS median_price,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price_charged)::NUMERIC, 2) AS p75_price,
    ROUND(MAX(price_charged)::NUMERIC, 2)                              AS max_price_charged,
    ROUND(SUM(promo_flag) * 100.0 / COUNT(*), 1)                       AS promo_frequency_pct
FROM sales_data
GROUP BY category, market
ORDER BY category, market;


-- 2.4  Cross-elasticity signal: do competitor price changes affect Nestlé volume?
--      Join competitor prices with Nestlé sales on same week / category / market
-- -----------------------------------------------------------------------------
WITH nestle_weekly AS (
    SELECT week, category, market,
           SUM(volume_units) AS nestle_volume,
           AVG(price_charged) AS nestle_price
    FROM sales_data
    GROUP BY week, category, market
),
comp_weekly AS (
    SELECT week, category, market,
           AVG(competitor_price) AS avg_comp_price,
           AVG(price_index)      AS avg_price_index
    FROM competitor_prices
    GROUP BY week, category, market
)
SELECT
    n.week,
    n.category,
    n.market,
    n.nestle_volume,
    n.nestle_price,
    c.avg_comp_price,
    c.avg_price_index,
    ROUND((n.nestle_price - c.avg_comp_price)::NUMERIC, 2)  AS price_gap_eur,
    ROUND((n.nestle_price / NULLIF(c.avg_comp_price, 0) - 1) * 100, 1) AS nestle_price_premium_pct
FROM nestle_weekly n
JOIN comp_weekly c USING (week, category, market)
ORDER BY n.category, n.market, n.week;


-- =============================================================================
-- SECTION 3: MARKETING MIX & ROI
-- =============================================================================

-- 3.1  Marketing ROI by channel (revenue driven per EUR spent)
--      Uses MMM contribution table + total revenue
-- -----------------------------------------------------------------------------
WITH rev AS (
    SELECT week, category, market, SUM(revenue_eur) AS total_revenue
    FROM sales_data
    GROUP BY week, category, market
),
contrib AS (
    SELECT week, category, market,
           tv_contribution, digital_contribution,
           social_contribution, promo_contribution
    FROM mmm_contributions
),
spend AS (
    SELECT week, category, market,
           spend_tv, spend_digital, spend_social_media AS spend_social,
           total_marketing_spend
    FROM marketing_spend
)
SELECT
    s.category,
    s.market,
    ROUND(SUM(s.spend_tv), 0)                                         AS total_tv_spend,
    ROUND(SUM(r.total_revenue * c.tv_contribution), 0)                AS tv_driven_revenue,
    ROUND(SUM(r.total_revenue * c.tv_contribution) / NULLIF(SUM(s.spend_tv), 0), 2) AS tv_roi,
    ROUND(SUM(s.spend_digital), 0)                                    AS total_digital_spend,
    ROUND(SUM(r.total_revenue * c.digital_contribution), 0)           AS digital_driven_revenue,
    ROUND(SUM(r.total_revenue * c.digital_contribution) / NULLIF(SUM(s.spend_digital), 0), 2) AS digital_roi,
    ROUND(SUM(s.spend_social), 0)                                     AS total_social_spend,
    ROUND(SUM(r.total_revenue * c.social_contribution), 0)            AS social_driven_revenue,
    ROUND(SUM(r.total_revenue * c.social_contribution) / NULLIF(SUM(s.spend_social), 0), 2) AS social_roi
FROM spend s
JOIN rev   r USING (week, category, market)
JOIN contrib c USING (week, category, market)
GROUP BY s.category, s.market
ORDER BY tv_roi DESC;


-- 3.2  Diminishing returns: marketing spend vs incremental revenue by quartile
-- -----------------------------------------------------------------------------
WITH weekly_totals AS (
    SELECT
        m.week, m.category, m.market,
        m.total_marketing_spend,
        s.total_rev,
        NTILE(4) OVER (PARTITION BY m.category, m.market ORDER BY m.total_marketing_spend) AS spend_quartile
    FROM marketing_spend m
    JOIN (
        SELECT week, category, market, SUM(revenue_eur) AS total_rev
        FROM sales_data GROUP BY week, category, market
    ) s USING (week, category, market)
)
SELECT
    category, market, spend_quartile,
    ROUND(AVG(total_marketing_spend)::NUMERIC, 0)  AS avg_spend,
    ROUND(AVG(total_rev)::NUMERIC, 0)              AS avg_revenue,
    ROUND(AVG(total_rev) / NULLIF(AVG(total_marketing_spend), 0), 2) AS marginal_roi
FROM weekly_totals
GROUP BY category, market, spend_quartile
ORDER BY category, market, spend_quartile;


-- 3.3  Seasonality-adjusted marketing efficiency index
-- -----------------------------------------------------------------------------
WITH base AS (
    SELECT
        category, market,
        AVG(total_marketing_spend)  AS mean_spend,
        STDDEV(total_marketing_spend) AS std_spend
    FROM marketing_spend
    GROUP BY category, market
)
SELECT
    m.week,
    m.category,
    m.market,
    m.total_marketing_spend,
    ROUND(((m.total_marketing_spend - b.mean_spend) / NULLIF(b.std_spend, 0))::NUMERIC, 2) AS spend_z_score,
    CASE
        WHEN (m.total_marketing_spend - b.mean_spend) / NULLIF(b.std_spend, 0) > 1.5  THEN 'High Investment Week'
        WHEN (m.total_marketing_spend - b.mean_spend) / NULLIF(b.std_spend, 0) < -1.5 THEN 'Low Investment Week'
        ELSE 'Normal Week'
    END AS investment_intensity
FROM marketing_spend m
JOIN base b USING (category, market)
ORDER BY m.category, m.market, m.week;


-- =============================================================================
-- SECTION 4: CUSTOMER SEGMENTATION & CLV
-- =============================================================================

-- 4.1  Segment profile summary
-- -----------------------------------------------------------------------------
SELECT
    segment,
    COUNT(*)                                              AS customer_count,
    ROUND(AVG(monthly_spend_eur)::NUMERIC, 2)            AS avg_monthly_spend,
    ROUND(AVG(monthly_visits)::NUMERIC, 1)               AS avg_monthly_visits,
    ROUND(AVG(brand_loyalty_score)::NUMERIC, 3)          AS avg_loyalty,
    ROUND(AVG(promo_sensitivity)::NUMERIC, 3)            AS avg_promo_sensitivity,
    ROUND(AVG(clv_12m_eur)::NUMERIC, 2)                  AS avg_clv_12m,
    ROUND(AVG(nps_score)::NUMERIC, 1)                    AS avg_nps,
    ROUND(AVG(churn_risk_score)::NUMERIC, 3)             AS avg_churn_risk,
    ROUND(SUM(clv_12m_eur), 0)                           AS total_clv_12m
FROM customer_data
GROUP BY segment
ORDER BY avg_clv_12m DESC;


-- 4.2  High-value at-risk customers (churn risk > 0.6, CLV top quartile)
-- -----------------------------------------------------------------------------
WITH clv_quartile AS (
    SELECT customer_id, clv_12m_eur,
           NTILE(4) OVER (ORDER BY clv_12m_eur DESC) AS clv_quartile
    FROM customer_data
)
SELECT
    c.customer_id,
    c.segment,
    c.market,
    c.monthly_spend_eur,
    c.clv_12m_eur,
    c.churn_risk_score,
    c.brand_loyalty_score,
    c.nps_score,
    CASE
        WHEN c.churn_risk_score > 0.75 THEN 'Critical'
        WHEN c.churn_risk_score > 0.60 THEN 'High'
        ELSE 'Medium'
    END AS churn_risk_tier
FROM customer_data c
JOIN clv_quartile q USING (customer_id)
WHERE q.clv_quartile = 1
  AND c.churn_risk_score > 0.60
ORDER BY c.clv_12m_eur DESC, c.churn_risk_score DESC
LIMIT 100;


-- 4.3  Digital vs non-digital customer comparison
-- -----------------------------------------------------------------------------
SELECT
    digital_active,
    segment,
    COUNT(*)                                            AS n_customers,
    ROUND(AVG(monthly_spend_eur)::NUMERIC, 2)          AS avg_spend,
    ROUND(AVG(clv_12m_eur)::NUMERIC, 2)                AS avg_clv,
    ROUND(AVG(promo_sensitivity)::NUMERIC, 3)          AS avg_promo_sens,
    ROUND(AVG(churn_risk_score)::NUMERIC, 3)           AS avg_churn_risk,
    ROUND(AVG(nps_score)::NUMERIC, 1)                  AS avg_nps
FROM customer_data
GROUP BY digital_active, segment
ORDER BY digital_active DESC, avg_clv DESC;


-- 4.4  RFM-style scoring (Recency proxy = inverse churn risk, Frequency = visits, Monetary = spend)
-- -----------------------------------------------------------------------------
WITH rfm_raw AS (
    SELECT
        customer_id, segment, market,
        NTILE(5) OVER (ORDER BY (1 - churn_risk_score) DESC)  AS r_score,  -- proxy for recency
        NTILE(5) OVER (ORDER BY monthly_visits DESC)           AS f_score,
        NTILE(5) OVER (ORDER BY monthly_spend_eur DESC)        AS m_score
    FROM customer_data
)
SELECT
    customer_id,
    segment,
    market,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score                  AS rfm_total,
    CASE
        WHEN r_score + f_score + m_score >= 13 THEN 'Champions'
        WHEN r_score + f_score + m_score >= 10 THEN 'Loyal Customers'
        WHEN r_score + f_score + m_score >= 7  THEN 'Potential Loyalists'
        WHEN f_score <= 2 AND r_score >= 4     THEN 'New Customers'
        WHEN r_score <= 2 AND f_score >= 4     THEN 'At Risk'
        ELSE 'Needs Attention'
    END AS rfm_segment
FROM rfm_raw
ORDER BY rfm_total DESC;


-- =============================================================================
-- SECTION 5: EXPERIMENTATION & CAUSAL INFERENCE
-- =============================================================================

-- 5.1  Experiment results summary with statistical significance
-- -----------------------------------------------------------------------------
SELECT
    experiment_name,
    category,
    market,
    start_date,
    end_date,
    control_size,
    treatment_size,
    control_conversion_pct,
    treatment_conversion_pct,
    observed_lift_pct,
    z_score,
    p_value,
    CASE WHEN significant_95 = 1 THEN 'Yes ✓' ELSE 'No ✗' END AS statistically_significant,
    incremental_revenue_eur,
    ROUND(incremental_revenue_eur / NULLIF(treatment_size, 0), 2) AS revenue_per_treated_customer
FROM experiments
ORDER BY observed_lift_pct DESC;


-- 5.2  Average treatment effect (ATE) and experiment ROI
-- -----------------------------------------------------------------------------
SELECT
    category,
    COUNT(*)                                               AS n_experiments,
    ROUND(AVG(observed_lift_pct)::NUMERIC, 1)             AS avg_lift_pct,
    ROUND(AVG(CASE WHEN significant_95 = 1 THEN observed_lift_pct END)::NUMERIC, 1) AS avg_significant_lift_pct,
    SUM(CASE WHEN significant_95 = 1 THEN 1 ELSE 0 END)  AS significant_experiments,
    ROUND(SUM(incremental_revenue_eur), 0)                AS total_incremental_revenue,
    ROUND(AVG(p_value)::NUMERIC, 4)                       AS avg_p_value
FROM experiments
GROUP BY category
ORDER BY avg_lift_pct DESC;


-- =============================================================================
-- SECTION 6: INTEGRATED VIEW — SALES + MARKETING + COMPETITOR
-- =============================================================================

-- 6.1  Full weekly performance dashboard view
--      (suitable as a base for a BI tool / dashboard)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_weekly_performance AS
WITH sales_agg AS (
    SELECT
        week, category, market,
        SUM(revenue_eur)          AS revenue,
        SUM(volume_units)         AS volume,
        SUM(gross_profit_eur)     AS gross_profit,
        AVG(price_charged)        AS avg_price,
        AVG(gross_margin_pct)     AS avg_margin,
        SUM(promo_flag)::FLOAT / COUNT(*) AS promo_rate
    FROM sales_data
    GROUP BY week, category, market
),
mkt_agg AS (
    SELECT week, category, market, total_marketing_spend AS mkt_spend
    FROM marketing_spend
),
comp_agg AS (
    SELECT week, category, market,
           AVG(price_index) AS avg_comp_price_index
    FROM competitor_prices
    GROUP BY week, category, market
)
SELECT
    s.week, s.category, s.market,
    s.revenue, s.volume, s.gross_profit,
    ROUND(s.avg_price::NUMERIC, 2)              AS avg_price,
    ROUND(s.avg_margin::NUMERIC, 1)             AS avg_margin_pct,
    ROUND(s.promo_rate * 100, 1)                AS promo_rate_pct,
    m.mkt_spend,
    ROUND(s.revenue / NULLIF(m.mkt_spend, 0), 2) AS marketing_roi,
    c.avg_comp_price_index
FROM sales_agg s
LEFT JOIN mkt_agg  m USING (week, category, market)
LEFT JOIN comp_agg c USING (week, category, market);


-- 6.2  Category health scorecard (annual)
-- -----------------------------------------------------------------------------
SELECT
    s.category,
    s.year,
    ROUND(SUM(s.revenue_eur) / 1e6, 2)             AS revenue_meur,
    ROUND(AVG(s.gross_margin_pct), 1)              AS avg_margin_pct,
    ROUND(SUM(m.total_marketing_spend) / 1e6, 2)  AS mkt_spend_meur,
    ROUND(SUM(s.revenue_eur) / NULLIF(SUM(m.total_marketing_spend), 0), 2) AS overall_roi,
    ROUND(AVG(c.avg_comp_price_index), 1)          AS avg_comp_price_idx,
    ROUND(AVG(s.price_charged), 2)                 AS avg_nestle_price,
    ROUND(SUM(s.promo_flag)::FLOAT / COUNT(*) * 100, 1) AS promo_freq_pct
FROM sales_data s
LEFT JOIN marketing_spend m  USING (week, category, market)
LEFT JOIN (
    SELECT week, category, market, AVG(price_index) AS avg_comp_price_index
    FROM competitor_prices
    GROUP BY week, category, market
) c USING (week, category, market)
GROUP BY s.category, s.year
ORDER BY s.category, s.year;
