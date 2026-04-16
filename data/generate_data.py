"""
Synthetic Data Generator for Nestlé NHS Global Data Analytics Project
======================================================================
Generates realistic FMCG sales, marketing, pricing and customer data
reflecting Nestlé's product portfolio and business structure.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import random

np.random.seed(42)
random.seed(42)

OUTPUT_DIR = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────
CATEGORIES = {
    "Coffee":       {"brands": ["Nescafé Classic", "Nescafé Gold", "Nespresso Original", "Nescafé Dolce Gusto"], "base_price": [3.99, 5.49, 6.99, 8.49]},
    "Chocolate":    {"brands": ["KitKat", "Smarties", "Aero", "Milkybar"],                                        "base_price": [1.29, 0.99, 1.49, 1.09]},
    "Water":        {"brands": ["Nestlé Pure Life", "S.Pellegrino", "Perrier", "Vittel"],                         "base_price": [0.69, 1.29, 1.49, 0.79]},
    "Dairy":        {"brands": ["Carnation", "Nesquik Milk", "LC1", "Sveltesse"],                                 "base_price": [1.89, 1.49, 2.29, 1.99]},
    "Baby Food":    {"brands": ["NAN", "Cerelac", "Nestum", "Gerber"],                                            "base_price": [9.99, 4.49, 3.99, 3.29]},
}

MARKETS = {
    "Spain":   {"pop_weight": 1.0,  "currency": "EUR", "price_adj": 1.00},
    "Germany": {"pop_weight": 1.8,  "currency": "EUR", "price_adj": 1.15},
    "France":  {"pop_weight": 1.4,  "currency": "EUR", "price_adj": 1.10},
    "UK":      {"pop_weight": 1.6,  "currency": "GBP", "price_adj": 1.05},
    "Italy":   {"pop_weight": 1.2,  "currency": "EUR", "price_adj": 0.95},
}

CHANNELS = ["Modern Trade", "E-Commerce", "Convenience", "Foodservice", "Pharmacy"]
CHANNEL_WEIGHTS = [0.45, 0.25, 0.15, 0.10, 0.05]

MARKETING_CHANNELS = ["TV", "Digital", "Social Media", "Out-of-Home", "Print", "Sponsorship"]

START_DATE = pd.Timestamp("2024-01-01")
END_DATE   = pd.Timestamp("2025-12-29")
WEEKS = pd.date_range(START_DATE, END_DATE, freq="W-MON")


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────
def seasonal_index(week: pd.Timestamp, category: str) -> float:
    """Return a multiplicative seasonal factor (1.0 = baseline)."""
    month = week.month
    PROFILES = {
        "Coffee":    [1.20, 1.15, 1.00, 0.90, 0.85, 0.80, 0.78, 0.82, 0.95, 1.05, 1.15, 1.30],
        "Chocolate": [0.90, 0.95, 1.20, 1.10, 0.85, 0.80, 0.85, 0.88, 0.90, 1.00, 1.25, 1.60],
        "Water":     [0.70, 0.72, 0.80, 0.90, 1.10, 1.35, 1.55, 1.50, 1.20, 0.95, 0.80, 0.75],
        "Dairy":     [1.05, 1.00, 1.00, 0.98, 1.00, 1.02, 1.05, 1.03, 1.00, 1.00, 1.05, 1.10],
        "Baby Food": [1.05, 1.02, 1.00, 1.00, 0.98, 0.98, 1.00, 1.00, 1.02, 1.03, 1.05, 1.07],
    }
    return PROFILES[category][month - 1]


def trend_factor(week: pd.Timestamp, category: str) -> float:
    """Linear + category-specific trend over the 2-year period."""
    TRENDS = {"Coffee": 0.08, "Chocolate": 0.03, "Water": 0.12, "Dairy": -0.02, "Baby Food": 0.05}
    elapsed = (week - START_DATE).days / 365
    return 1 + TRENDS[category] * elapsed


def price_with_promotion(base: float, promo: bool, depth: float = 0.0) -> float:
    return round(base * (1 - depth) if promo else base, 2)


# ─────────────────────────────────────────────────────────────────
# TABLE 1 — WEEKLY SALES DATA
# ─────────────────────────────────────────────────────────────────
def generate_sales_data() -> pd.DataFrame:
    records = []
    promo_calendar = {}  # (brand, market, week) -> (is_promo, depth)

    for cat, meta in CATEGORIES.items():
        for brand, base_price in zip(meta["brands"], meta["base_price"]):
            for market, mdata in MARKETS.items():
                base_vol = np.random.randint(400, 2500) * mdata["pop_weight"]
                adj_price = round(base_price * mdata["price_adj"], 2)
                elasticity = np.random.uniform(-2.8, -0.9)   # own-price elasticity
                promo_prob  = np.random.uniform(0.08, 0.20)   # % of weeks on promo

                for week in WEEKS:
                    is_promo = np.random.random() < promo_prob
                    promo_depth = np.random.uniform(0.10, 0.35) if is_promo else 0.0
                    price_charged = price_with_promotion(adj_price, is_promo, promo_depth)

                    price_effect = (price_charged / adj_price) ** elasticity
                    season_eff   = seasonal_index(week, cat)
                    trend_eff    = trend_factor(week, cat)
                    noise        = np.random.lognormal(0, 0.08)

                    volume = round(base_vol * price_effect * season_eff * trend_eff * noise)

                    channel = np.random.choice(CHANNELS, p=CHANNEL_WEIGHTS)
                    revenue = round(price_charged * volume, 2)
                    cogs    = round(revenue * np.random.uniform(0.38, 0.52), 2)

                    records.append({
                        "week":             week,
                        "year":             week.year,
                        "quarter":          f"Q{week.quarter}",
                        "month":            week.strftime("%B"),
                        "category":         cat,
                        "brand":            brand,
                        "market":           market,
                        "channel":          channel,
                        "regular_price":    adj_price,
                        "price_charged":    price_charged,
                        "promo_flag":       int(is_promo),
                        "promo_depth_pct":  round(promo_depth * 100, 1),
                        "volume_units":     int(volume),
                        "revenue_eur":      revenue,
                        "cogs_eur":         cogs,
                        "gross_profit_eur": round(revenue - cogs, 2),
                        "elasticity":       round(elasticity, 4),
                    })

    df = pd.DataFrame(records)
    df["gross_margin_pct"] = round(df["gross_profit_eur"] / df["revenue_eur"] * 100, 2)
    return df


# ─────────────────────────────────────────────────────────────────
# TABLE 2 — WEEKLY MARKETING SPEND
# ─────────────────────────────────────────────────────────────────
def generate_marketing_data() -> pd.DataFrame:
    records = []
    total_annual_budget = {
        "Coffee":    3_200_000,
        "Chocolate": 2_100_000,
        "Water":     1_500_000,
        "Dairy":     1_100_000,
        "Baby Food": 1_800_000,
    }
    channel_mix = {
        "Coffee":    [0.30, 0.28, 0.20, 0.10, 0.07, 0.05],
        "Chocolate": [0.35, 0.22, 0.18, 0.12, 0.08, 0.05],
        "Water":     [0.20, 0.30, 0.25, 0.15, 0.05, 0.05],
        "Dairy":     [0.28, 0.25, 0.22, 0.12, 0.08, 0.05],
        "Baby Food": [0.25, 0.30, 0.20, 0.08, 0.12, 0.05],
    }

    for cat, annual in total_annual_budget.items():
        for market, mdata in MARKETS.items():
            market_budget = annual * mdata["pop_weight"] / sum(v["pop_weight"] for v in MARKETS.values())
            weekly_base   = market_budget / 104   # 2 years

            for week in WEEKS:
                season_boost = seasonal_index(week, cat) * 0.6 + 0.4
                total_spend  = weekly_base * season_boost * np.random.lognormal(0, 0.12)

                row = {"week": week, "category": cat, "market": market}
                for ch, w in zip(MARKETING_CHANNELS, channel_mix[cat]):
                    spend = round(total_spend * w * np.random.uniform(0.85, 1.15), 2)
                    row[f"spend_{ch.lower().replace(' ', '_')}"] = spend
                row["total_marketing_spend"] = round(sum(row[f"spend_{c.lower().replace(' ', '_')}"] for c in MARKETING_CHANNELS), 2)

                # Derived metrics
                row["grp_tv"]       = round(row["spend_tv"] / 1200 * np.random.uniform(0.9, 1.1), 1)
                row["impressions_digital"] = int(row["spend_digital"] / 0.008 * np.random.uniform(0.9, 1.1))
                records.append(row)

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────
# TABLE 3 — CUSTOMER SEGMENTATION DATA
# ─────────────────────────────────────────────────────────────────
def generate_customer_data(n: int = 8000) -> pd.DataFrame:
    segments = {
        "Health Conscious":    {"weight": 0.22, "avg_spend": 85,  "visit_freq": 3.8, "brand_loyalty": 0.72, "promo_sensitivity": 0.35},
        "Family Shoppers":     {"weight": 0.28, "avg_spend": 120, "visit_freq": 4.5, "brand_loyalty": 0.55, "promo_sensitivity": 0.65},
        "Premium Seekers":     {"weight": 0.15, "avg_spend": 150, "visit_freq": 2.5, "brand_loyalty": 0.80, "promo_sensitivity": 0.20},
        "Budget Conscious":    {"weight": 0.20, "avg_spend": 55,  "visit_freq": 3.2, "brand_loyalty": 0.38, "promo_sensitivity": 0.85},
        "Convenience Buyers":  {"weight": 0.15, "avg_spend": 70,  "visit_freq": 2.0, "brand_loyalty": 0.45, "promo_sensitivity": 0.50},
    }

    seg_names = list(segments.keys())
    seg_weights = [v["weight"] for v in segments.values()]

    records = []
    for cid in range(1, n + 1):
        seg = np.random.choice(seg_names, p=seg_weights)
        s   = segments[seg]

        monthly_spend    = max(10, np.random.normal(s["avg_spend"],    s["avg_spend"] * 0.25))
        monthly_visits   = max(1,  np.random.normal(s["visit_freq"],   s["visit_freq"] * 0.30))
        brand_loyalty    = np.clip(np.random.normal(s["brand_loyalty"], 0.12), 0, 1)
        promo_sens       = np.clip(np.random.normal(s["promo_sensitivity"], 0.12), 0, 1)
        age              = int(np.clip(np.random.normal(38, 12), 18, 75))
        tenure_months    = int(np.random.exponential(24) + 1)
        pref_category    = np.random.choice(list(CATEGORIES.keys()), p=[0.30, 0.20, 0.18, 0.18, 0.14])
        pref_channel     = np.random.choice(CHANNELS, p=CHANNEL_WEIGHTS)
        digital_active   = int(np.random.random() < (0.30 + 0.5 * promo_sens))
        nps_score        = int(np.clip(np.random.normal(7.2 + brand_loyalty * 2, 1.5), 0, 10))
        churn_risk       = round(np.clip(0.6 - brand_loyalty * 0.5 - monthly_visits * 0.05 + promo_sens * 0.1, 0.02, 0.95), 3)
        clv_12m          = round(monthly_spend * monthly_visits * 12 * brand_loyalty * 0.9, 2)
        market           = np.random.choice(list(MARKETS.keys()), p=[0.25, 0.22, 0.20, 0.18, 0.15])

        records.append({
            "customer_id":         f"C{cid:06d}",
            "segment":             seg,
            "market":              market,
            "age":                 age,
            "tenure_months":       tenure_months,
            "monthly_spend_eur":   round(monthly_spend, 2),
            "monthly_visits":      round(monthly_visits, 1),
            "brand_loyalty_score": round(brand_loyalty, 3),
            "promo_sensitivity":   round(promo_sens, 3),
            "preferred_category":  pref_category,
            "preferred_channel":   pref_channel,
            "digital_active":      digital_active,
            "nps_score":           nps_score,
            "churn_risk_score":    churn_risk,
            "clv_12m_eur":         clv_12m,
        })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────
# TABLE 4 — COMPETITOR PRICE TRACKER
# ─────────────────────────────────────────────────────────────────
def generate_competitor_data(sales_df: pd.DataFrame) -> pd.DataFrame:
    competitors = {
        "Coffee":    ["Jacobs", "Lavazza", "Melitta"],
        "Chocolate": ["Mars", "Ferrero", "Lindt"],
        "Water":     ["Evian", "Volvic", "Aqua Panna"],
        "Dairy":     ["Danone", "Arla", "Müller"],
        "Baby Food": ["Hipp", "Aptamil", "Nutrilon"],
    }

    records = []
    ref_prices = sales_df.groupby(["week", "category", "market"])["regular_price"].mean().reset_index()

    for _, row in ref_prices.iterrows():
        for comp in competitors.get(row["category"], []):
            comp_price = round(row["regular_price"] * np.random.uniform(0.85, 1.20), 2)
            records.append({
                "week":             row["week"],
                "category":         row["category"],
                "market":           row["market"],
                "competitor":       comp,
                "competitor_price": comp_price,
                "price_index":      round(comp_price / row["regular_price"] * 100, 1),
            })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────
# TABLE 5 — EXPERIMENT / A-B TEST LOG
# ─────────────────────────────────────────────────────────────────
def generate_experiment_data() -> pd.DataFrame:
    experiments = [
        {"name": "Digital Coupon E-Commerce", "category": "Coffee",    "market": "Spain",   "start": "2023-03-06", "end": "2023-04-17", "treatment_lift_pct": 14.2, "control_size": 5000, "treatment_size": 5100},
        {"name": "Price -10% Promo Chocolate","category": "Chocolate", "market": "Germany", "start": "2023-05-01", "end": "2023-05-28", "treatment_lift_pct": 22.5, "control_size": 8000, "treatment_size": 7900},
        {"name": "In-Store Display Water",    "category": "Water",     "market": "France",  "start": "2023-06-05", "end": "2023-07-03", "treatment_lift_pct": 8.7,  "control_size": 6000, "treatment_size": 6200},
        {"name": "Loyalty Reward Dairy",      "category": "Dairy",     "market": "UK",      "start": "2023-09-04", "end": "2023-10-02", "treatment_lift_pct": 5.3,  "control_size": 4500, "treatment_size": 4400},
        {"name": "TV Flight Baby Food",       "category": "Baby Food", "market": "Italy",   "start": "2023-11-06", "end": "2023-12-04", "treatment_lift_pct": 11.8, "control_size": 3000, "treatment_size": 3100},
        {"name": "Email Retargeting Coffee",  "category": "Coffee",    "market": "UK",      "start": "2024-01-08", "end": "2024-02-05", "treatment_lift_pct": 9.1,  "control_size": 5500, "treatment_size": 5600},
        {"name": "Bundle Deal Chocolate",     "category": "Chocolate", "market": "Spain",   "start": "2024-03-04", "end": "2024-04-01", "treatment_lift_pct": 18.3, "control_size": 7000, "treatment_size": 6800},
        {"name": "SEM Bidding Water",         "category": "Water",     "market": "Germany", "start": "2024-05-06", "end": "2024-06-03", "treatment_lift_pct": 6.4,  "control_size": 9000, "treatment_size": 8900},
        {"name": "Shelf Placement Dairy",     "category": "Dairy",     "market": "France",  "start": "2024-07-01", "end": "2024-07-29", "treatment_lift_pct": 4.1,  "control_size": 4000, "treatment_size": 4100},
        {"name": "Influencer Baby Food",      "category": "Baby Food", "market": "Spain",   "start": "2024-09-02", "end": "2024-09-30", "treatment_lift_pct": 13.6, "control_size": 2500, "treatment_size": 2600},
    ]

    records = []
    for exp in experiments:
        lift = exp["treatment_lift_pct"] / 100
        n_c  = exp["control_size"]
        n_t  = exp["treatment_size"]
        p_c  = np.random.uniform(0.08, 0.18)
        p_t  = p_c * (1 + lift)
        se   = np.sqrt(p_c * (1 - p_c) / n_c + p_t * (1 - p_t) / n_t)
        z    = (p_t - p_c) / se
        p_val = round(2 * (1 - 0.5 * (1 + np.sign(z) * (1 - np.exp(-0.717 * abs(z) - 0.416 * z**2)))), 4)

        records.append({
            "experiment_name":        exp["name"],
            "category":               exp["category"],
            "market":                 exp["market"],
            "start_date":             exp["start"],
            "end_date":               exp["end"],
            "control_size":           n_c,
            "treatment_size":         n_t,
            "control_conversion_pct": round(p_c * 100, 2),
            "treatment_conversion_pct": round(p_t * 100, 2),
            "observed_lift_pct":      exp["treatment_lift_pct"],
            "z_score":                round(z, 3),
            "p_value":                p_val,
            "significant_95":         int(p_val < 0.05),
            "incremental_revenue_eur": round(np.random.uniform(15000, 85000), 0),
        })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────
# TABLE 6 — MMM CONTRIBUTION TABLE (pre-computed for dashboard)
# ─────────────────────────────────────────────────────────────────
def generate_mmm_contributions(sales_df: pd.DataFrame, mkt_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for cat in CATEGORIES:
        for market in MARKETS:
            for week in WEEKS:
                base_vol  = np.random.uniform(0.50, 0.65)
                tv_cont   = np.random.uniform(0.06, 0.14)
                dig_cont  = np.random.uniform(0.05, 0.12)
                soc_cont  = np.random.uniform(0.02, 0.08)
                promo_cont = np.random.uniform(0.04, 0.12)
                season_cont = 1 - base_vol - tv_cont - dig_cont - soc_cont - promo_cont
                records.append({
                    "week": week, "category": cat, "market": market,
                    "base_contribution": round(base_vol, 4),
                    "tv_contribution":   round(tv_cont, 4),
                    "digital_contribution": round(dig_cont, 4),
                    "social_contribution":  round(soc_cont, 4),
                    "promo_contribution":   round(promo_cont, 4),
                    "seasonal_contribution": round(season_cont, 4),
                })
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating Nestlé synthetic dataset …")

    print("  [1/6] Weekly sales data …")
    sales = generate_sales_data()
    sales.to_csv(OUTPUT_DIR / "sales_data.csv", index=False)
    print(f"        → {len(sales):,} rows saved to sales_data.csv")

    print("  [2/6] Marketing spend data …")
    mkt = generate_marketing_data()
    mkt.to_csv(OUTPUT_DIR / "marketing_spend.csv", index=False)
    print(f"        → {len(mkt):,} rows saved to marketing_spend.csv")

    print("  [3/6] Customer segmentation data …")
    cust = generate_customer_data()
    cust.to_csv(OUTPUT_DIR / "customer_data.csv", index=False)
    print(f"        → {len(cust):,} rows saved to customer_data.csv")

    print("  [4/6] Competitor price tracker …")
    comp = generate_competitor_data(sales)
    comp.to_csv(OUTPUT_DIR / "competitor_prices.csv", index=False)
    print(f"        → {len(comp):,} rows saved to competitor_prices.csv")

    print("  [5/6] A/B experiment log …")
    exp = generate_experiment_data()
    exp.to_csv(OUTPUT_DIR / "experiments.csv", index=False)
    print(f"        → {len(exp):,} rows saved to experiments.csv")

    print("  [6/6] MMM contribution table …")
    mmm = generate_mmm_contributions(sales, mkt)
    mmm.to_csv(OUTPUT_DIR / "mmm_contributions.csv", index=False)
    print(f"        → {len(mmm):,} rows saved to mmm_contributions.csv")

    print("\nAll datasets generated successfully.")
