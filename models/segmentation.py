"""
Customer Segmentation Model
============================
K-Means clustering on customer behavioural features.
Also computes RFM scores and churn propensity.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data"


def run_kmeans_segmentation(df: pd.DataFrame, n_clusters: int = 5,
                             features: list = None) -> pd.DataFrame:
    """
    Fit K-Means on customer features and return labelled DataFrame.
    """
    if features is None:
        features = ["monthly_spend_eur", "monthly_visits", "brand_loyalty_score",
                    "promo_sensitivity", "tenure_months", "clv_12m_eur"]

    X = df[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
    labels = km.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, labels)
    print(f"K-Means silhouette score (k={n_clusters}): {sil:.3f}")

    df = df.copy()
    df["ml_cluster"] = labels

    # PCA for 2D visualisation
    pca = PCA(n_components=2, random_state=42)
    comps = pca.fit_transform(X_scaled)
    df["pca_1"] = comps[:, 0]
    df["pca_2"] = comps[:, 1]
    df["pca_var_explained"] = round(sum(pca.explained_variance_ratio_) * 100, 1)

    return df, km, scaler, sil


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """
    RFM scoring — proxy using available columns.
      R (Recency)   → inverse of churn risk (higher churn risk = less recent)
      F (Frequency) → monthly_visits
      M (Monetary)  → monthly_spend_eur
    """
    df = df.copy()
    df["R_raw"] = 1 - df["churn_risk_score"]
    df["F_raw"] = df["monthly_visits"]
    df["M_raw"] = df["monthly_spend_eur"]

    for col in ["R_raw", "F_raw", "M_raw"]:
        df[col.replace("_raw", "_score")] = pd.qcut(df[col], q=5, labels=[1, 2, 3, 4, 5]).astype(int)

    df["rfm_total"] = df["R_score"] + df["F_score"] + df["M_score"]
    df["rfm_segment"] = df["rfm_total"].apply(
        lambda x: "Champions"         if x >= 13 else
                  "Loyal Customers"   if x >= 10 else
                  "Potential Loyalists" if x >= 8 else
                  "At Risk"           if x <= 6 else
                  "Needs Attention"
    )
    return df


def find_optimal_k(df: pd.DataFrame, features: list, k_range=range(2, 10)) -> pd.DataFrame:
    """Elbow method + silhouette to find optimal number of clusters."""
    X = df[features].fillna(0)
    X_scaled = StandardScaler().fit_transform(X)

    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels) if k > 1 else 0
        rows.append({"k": k, "inertia": km.inertia_, "silhouette": round(sil, 4)})

    return pd.DataFrame(rows)


if __name__ == "__main__":
    cust = pd.read_csv(DATA_DIR / "customer_data.csv")
    print(f"Loaded {len(cust):,} customers\n")

    # Find optimal k
    print("── ELBOW ANALYSIS ──────────────────────────────────")
    features = ["monthly_spend_eur", "monthly_visits", "brand_loyalty_score",
                "promo_sensitivity", "tenure_months", "clv_12m_eur"]
    elbow = find_optimal_k(cust, features)
    print(elbow.to_string(index=False))

    # Fit model
    print("\n── K-MEANS SEGMENTATION (k=5) ──────────────────────")
    cust_labelled, model, scaler, sil = run_kmeans_segmentation(cust, n_clusters=5)

    cluster_summary = cust_labelled.groupby("ml_cluster")[features].mean().round(2)
    print("\nCluster centroids (feature means):")
    print(cluster_summary.to_string())

    # RFM
    print("\n── RFM SCORING ─────────────────────────────────────")
    cust_rfm = compute_rfm(cust_labelled)
    print(cust_rfm["rfm_segment"].value_counts().to_string())

    out_path = DATA_DIR / "customer_segmented.csv"
    cust_rfm.to_csv(out_path, index=False)
    print(f"\nSaved segmented data to {out_path}")
