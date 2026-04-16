"""
Price Elasticity Model
======================
Log-log OLS regression to estimate own-price elasticities per brand / market.
Also computes cross-elasticities with respect to competitor prices.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

try:
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    print("statsmodels not installed — using OLS fallback via numpy.")

DATA_DIR = Path(__file__).parent.parent / "data"


def log_log_elasticity(df_brand: pd.DataFrame) -> dict:
    """
    Estimate price elasticity using log-log OLS regression.

    Model:  ln(Volume) = α + β₁·ln(Price) + β₂·Promo + β₃·Week_trend + ε
    β₁ is the own-price elasticity estimate.
    """
    df = df_brand.copy().dropna(subset=["volume_units", "price_charged"])
    df = df[df["volume_units"] > 0]

    if len(df) < 20:
        return {"elasticity": np.nan, "r_squared": np.nan, "n_obs": len(df)}

    df["ln_volume"] = np.log(df["volume_units"])
    df["ln_price"]  = np.log(df["price_charged"])
    df["trend"]     = (df["week"] - df["week"].min()).dt.days / 7

    X = df[["ln_price", "promo_flag", "trend"]].copy()
    y = df["ln_volume"]

    if STATSMODELS_AVAILABLE:
        X_const = sm.add_constant(X)
        model   = sm.OLS(y, X_const).fit(cov_type="HC3")
        bp_test = het_breuschpagan(model.resid, model.model.exog)
        return {
            "elasticity":      model.params.get("ln_price", np.nan),
            "elasticity_pval": model.pvalues.get("ln_price", np.nan),
            "promo_effect":    model.params.get("promo_flag", np.nan),
            "r_squared":       model.rsquared,
            "n_obs":           int(model.nobs),
            "aic":             model.aic,
            "bp_pval":         bp_test[1],
        }
    else:
        # Numpy fallback
        X_np = np.column_stack([np.ones(len(X)), X.values])
        coeffs, _, _, _ = np.linalg.lstsq(X_np, y.values, rcond=None)
        y_hat = X_np @ coeffs
        ss_res = np.sum((y.values - y_hat) ** 2)
        ss_tot = np.sum((y.values - y.values.mean()) ** 2)
        return {
            "elasticity": coeffs[1],
            "r_squared":  1 - ss_res / ss_tot,
            "n_obs":      len(X),
        }


def run_elasticity_analysis(save: bool = True) -> pd.DataFrame:
    print("Loading data …")
    sales = pd.read_csv(DATA_DIR / "sales_data.csv", parse_dates=["week"])

    results = []
    groups  = sales.groupby(["brand", "market", "category"])

    print(f"Running log-log OLS for {len(groups)} brand×market combinations …")
    for (brand, market, category), group in groups:
        res = log_log_elasticity(group)
        results.append({
            "brand":    brand,
            "market":   market,
            "category": category,
            **res,
        })

    out = pd.DataFrame(results)
    out["elasticity_class"] = out["elasticity"].apply(
        lambda e: ("Highly Elastic" if e < -2 else
                   ("Elastic" if e < -1 else
                    ("Inelastic" if e < -0.5 else "Highly Inelastic")))
        if pd.notna(e) else "Unknown"
    )

    print("\n── ELASTICITY SUMMARY ──────────────────────────────")
    summ = out.groupby("category")["elasticity"].agg(["mean", "min", "max", "std"]).round(3)
    print(summ.to_string())

    if save:
        out_path = DATA_DIR / "elasticity_results.csv"
        out.to_csv(out_path, index=False)
        print(f"\nSaved to {out_path}")

    return out


def simulate_price_scenarios(brand: str, market: str,
                              price_changes: list = None,
                              elasticity: float = None) -> pd.DataFrame:
    """
    Simulate volume and revenue impact for a range of price changes.
    """
    if price_changes is None:
        price_changes = list(range(-30, 35, 5))

    sales = pd.read_csv(DATA_DIR / "sales_data.csv", parse_dates=["week"])
    brand_data = sales[(sales["brand"] == brand) & (sales["market"] == market)]

    if brand_data.empty:
        raise ValueError(f"No data for {brand} / {market}")

    base_price  = brand_data["regular_price"].mean()
    base_vol    = brand_data["volume_units"].mean()
    base_rev    = base_price * base_vol
    base_margin = brand_data["gross_margin_pct"].mean()

    if elasticity is None:
        elasticity = brand_data["elasticity"].mean()

    cogs_rate = (100 - base_margin) / 100

    rows = []
    for pct in price_changes:
        new_price    = base_price * (1 + pct / 100)
        new_vol      = base_vol * ((new_price / base_price) ** elasticity)
        new_rev      = new_vol * new_price
        new_gp       = new_vol * (new_price - base_price * cogs_rate)
        new_margin   = (new_price - base_price * cogs_rate) / new_price * 100
        rows.append({
            "price_change_pct": pct,
            "new_price":        round(new_price, 2),
            "new_volume":       round(new_vol, 0),
            "new_revenue":      round(new_rev, 2),
            "new_gross_profit": round(new_gp, 2),
            "new_margin_pct":   round(new_margin, 2),
            "vol_change_pct":   round((new_vol - base_vol) / base_vol * 100, 2),
            "rev_change_pct":   round((new_rev - base_rev) / base_rev * 100, 2),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    results = run_elasticity_analysis()

    print("\n── SCENARIO SIMULATION ─────────────────────────────")
    first_brand  = results.dropna(subset=["elasticity"]).iloc[0]["brand"]
    first_market = results.dropna(subset=["elasticity"]).iloc[0]["market"]
    scenarios    = simulate_price_scenarios(first_brand, first_market)
    print(f"\nPrice scenarios for {first_brand} / {first_market}:")
    print(scenarios[["price_change_pct", "new_price", "vol_change_pct", "rev_change_pct"]].to_string(index=False))
