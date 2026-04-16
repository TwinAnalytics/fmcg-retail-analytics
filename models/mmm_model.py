"""
Marketing Mix Model (MMM)
=========================
Bayesian-inspired MMM using Adstock + Saturation transformations.
Estimates the contribution of each marketing channel to sales volume.
Implements Hill saturation and Geometric adstock (Robyn-style).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.optimize import minimize
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"


# ─────────────────────────────────────────────────────────────────
# TRANSFORMATIONS
# ─────────────────────────────────────────────────────────────────

def adstock(x: np.ndarray, theta: float) -> np.ndarray:
    """
    Geometric adstock: simulates carryover / lagged effect of advertising.
    theta ∈ [0, 1] — higher value = longer carryover.
    """
    result = np.zeros_like(x, dtype=float)
    result[0] = x[0]
    for t in range(1, len(x)):
        result[t] = x[t] + theta * result[t - 1]
    return result


def hill_saturation(x: np.ndarray, k: float, n: float) -> np.ndarray:
    """
    Hill function: models diminishing returns on spend.
    k = inflection point (50% saturation), n = slope steepness.
    """
    return x ** n / (k ** n + x ** n)


def transform_channel(x: np.ndarray, theta: float, k: float, n: float) -> np.ndarray:
    """Apply adstock then saturation."""
    x_ad  = adstock(x, theta)
    x_sat = hill_saturation(x_ad, k, n)
    return x_sat


# ─────────────────────────────────────────────────────────────────
# SIMPLE REGRESSION-BASED MMM
# ─────────────────────────────────────────────────────────────────

class SimpleMMM:
    """
    Lightweight MMM:
      1. Apply adstock + Hill saturation to each marketing channel.
      2. Fit OLS: Sales ~ Base + Σ β_c · X_c_transformed + Promo + Seasonality
      3. Decompose revenue contributions.
    """

    CHANNEL_PARAMS = {
        "tv":           {"theta": 0.40, "k": 0.50, "n": 2.5},
        "digital":      {"theta": 0.15, "k": 0.45, "n": 2.0},
        "social_media": {"theta": 0.20, "k": 0.40, "n": 1.8},
        "out_of_home":  {"theta": 0.30, "k": 0.55, "n": 2.2},
        "print":        {"theta": 0.10, "k": 0.60, "n": 1.5},
    }

    def __init__(self):
        self.coeffs_   = None
        self.channels_ = None
        self.r2_       = None

    def _build_features(self, sales_df, mkt_df):
        merged = sales_df.merge(mkt_df, on=["week", "category", "market"], how="left")
        merged = merged.sort_values("week").reset_index(drop=True)

        features = {}
        for ch, params in self.CHANNEL_PARAMS.items():
            col = f"spend_{ch}"
            if col in merged.columns:
                x_raw  = merged[col].fillna(0).values
                x_norm = x_raw / (x_raw.max() + 1e-9)
                features[ch] = transform_channel(x_norm, **params)

        df_feat = pd.DataFrame(features)
        df_feat["promo_flag"] = merged["promo_flag"].values
        df_feat["week_trend"] = np.arange(len(merged)) / len(merged)

        # Month seasonality dummies
        for month in range(2, 13):
            df_feat[f"m{month}"] = (merged["week"].dt.month == month).astype(int).values

        y = merged["volume_units"].values
        return df_feat, y, merged

    def fit(self, sales_df, mkt_df):
        X, y, _ = self._build_features(sales_df, mkt_df)
        self.channels_ = list(self.CHANNEL_PARAMS.keys())

        X_np    = np.column_stack([np.ones(len(X)), X.values])
        self.coeffs_, _, _, _ = np.linalg.lstsq(X_np, y, rcond=None)

        y_hat   = X_np @ self.coeffs_
        ss_res  = np.sum((y - y_hat) ** 2)
        ss_tot  = np.sum((y - y.mean()) ** 2)
        self.r2_ = 1 - ss_res / ss_tot

        return self

    def decompose(self, sales_df, mkt_df):
        X, y, merged = self._build_features(sales_df, mkt_df)
        X_np = np.column_stack([np.ones(len(X)), X.values])
        y_hat = X_np @ self.coeffs_

        contrib = pd.DataFrame({"week": merged["week"].values, "actual": y, "predicted": y_hat})
        contrib["base"] = self.coeffs_[0]

        col_names = ["const"] + list(X.columns)
        for i, name in enumerate(col_names[1:], 1):
            contrib[name] = self.coeffs_[i] * X[X.columns[i - 1]].values

        # Normalise contributions to sum to predicted
        channel_cols = [c for c in contrib.columns if c in self.channels_ or c == "base"]
        contrib["sum_parts"] = contrib[channel_cols].sum(axis=1)

        return contrib


# ─────────────────────────────────────────────────────────────────
# BUDGET OPTIMISER
# ─────────────────────────────────────────────────────────────────

def optimise_budget(total_budget: float, current_alloc: dict, roi_estimates: dict) -> dict:
    """
    Gradient-free budget optimisation under diminishing-returns assumption.
    Maximises total_driven_revenue = Σ ROI(c) * spend(c)
    subject to: Σ spend(c) = total_budget, spend(c) >= 0.

    Uses Lagrangian / marginal equalisation approach.
    """
    channels = list(roi_estimates.keys())
    n = len(channels)

    def neg_total_revenue(spends):
        return -sum(roi_estimates[c] * s for c, s in zip(channels, spends))

    constraints = [{"type": "eq", "fun": lambda x: sum(x) - total_budget}]
    bounds      = [(0, total_budget) for _ in channels]
    x0          = [total_budget / n] * n

    result = minimize(neg_total_revenue, x0, method="SLSQP",
                      bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-9, "maxiter": 1000})

    optimal = {c: round(s, 2) for c, s in zip(channels, result.x)}
    revenue  = {c: round(optimal[c] * roi_estimates[c], 2) for c in channels}

    return {
        "optimal_spend":    optimal,
        "driven_revenue":   revenue,
        "total_revenue":    round(sum(revenue.values()), 2),
        "current_revenue":  round(sum(roi_estimates[c] * current_alloc.get(c, 0) for c in channels), 2),
        "success":          result.success,
    }


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sales = pd.read_csv(DATA_DIR / "sales_data.csv", parse_dates=["week"])
    mkt   = pd.read_csv(DATA_DIR / "marketing_spend.csv", parse_dates=["week"])

    category = "Coffee"
    market   = "Spain"

    s_sub = sales[(sales["category"] == category) & (sales["market"] == market)].copy()
    s_sub = s_sub.groupby("week").agg(volume_units=("volume_units", "sum"),
                                       promo_flag=("promo_flag", "mean")).reset_index()
    s_sub["category"] = category
    s_sub["market"]   = market

    m_sub = mkt[(mkt["category"] == category) & (mkt["market"] == market)].copy()

    model = SimpleMMM().fit(s_sub, m_sub)
    print(f"MMM R² for {category} / {market}: {model.r2_:.3f}")

    decomp = model.decompose(s_sub, m_sub)
    print("\nContribution sample (last 5 weeks):")
    print(decomp[["week", "actual", "predicted", "base"]].tail(5).to_string(index=False))

    print("\n── BUDGET OPTIMISATION ─────────────────────────────")
    roi_est = {"tv": 3.8, "digital": 5.2, "social_media": 4.1, "out_of_home": 2.9, "print": 2.1}
    current = {"tv": 30000, "digital": 25000, "social_media": 15000, "out_of_home": 10000, "print": 5000}
    total_b = sum(current.values())

    opt = optimise_budget(total_b, current, roi_est)
    print(f"Current total revenue: €{opt['current_revenue']:,.0f}")
    print(f"Optimal total revenue: €{opt['total_revenue']:,.0f}")
    print(f"Revenue uplift:        €{opt['total_revenue'] - opt['current_revenue']:,.0f}")
    print("\nOptimal spend allocation:")
    for ch, spend in opt["optimal_spend"].items():
        print(f"  {ch:<15} €{spend:>8,.0f}  →  €{opt['driven_revenue'][ch]:>8,.0f} driven")
