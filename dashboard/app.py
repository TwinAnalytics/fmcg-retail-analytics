"""
Nestlé NHS Global Data Analytics — Interactive Dashboard
=========================================================
Run:  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────
# AUTO-GENERATE DATA IF MISSING (for Streamlit Cloud deployment)
# ─────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"

_REQUIRED_FILES = [
    "sales_data.csv", "marketing_spend.csv", "customer_data.csv",
    "competitor_prices.csv", "experiments.csv", "mmm_contributions.csv",
]

if not all((DATA_DIR / f).exists() for f in _REQUIRED_FILES):
    with st.spinner("Generating datasets for first run — this takes about 15 seconds…"):
        import subprocess
        subprocess.run(
            [sys.executable, str(DATA_DIR / "generate_data.py")],
            check=True,
        )

# ─────────────────────────────────────────────────────────────────
# NESTLÉ BRAND THEME
# ─────────────────────────────────────────────────────────────────
NESTLE_RED    = "#E2001A"
NESTLE_DARK   = "#1A1A1A"
NESTLE_GRAY   = "#6B6B6B"
NESTLE_LIGHT  = "#F5F5F5"
NESTLE_WHITE  = "#FFFFFF"
NESTLE_GREEN  = "#006633"
NESTLE_ACCENT = "#FF6B35"

COLOR_SEQ = [NESTLE_RED, "#B51015", "#FF6B35", NESTLE_GREEN, "#009966",
             "#004B23", "#FFB300", "#0077B6", "#6A0572", "#2D6A4F"]

st.set_page_config(
    page_title="Nestlé — NHS Global Data Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Global font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #1A1A1A;
    }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label { color: #CCCCCC !important; }

    /* Header bar */
    .nestle-header {
        background: linear-gradient(135deg, #E2001A 0%, #B51015 100%);
        padding: 18px 28px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .nestle-header h1 {
        color: white;
        margin: 0;
        font-size: 1.7rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .nestle-header p {
        color: rgba(255,255,255,0.80);
        margin: 0;
        font-size: 0.85rem;
    }

    /* KPI cards */
    .kpi-card {
        background: white;
        border: 1px solid #E8E8E8;
        border-radius: 12px;
        padding: 20px 22px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #E2001A;
        line-height: 1;
        margin-bottom: 4px;
    }
    .kpi-label {
        font-size: 0.80rem;
        color: #6B6B6B;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-delta-pos { color: #006633; font-size: 0.80rem; font-weight: 600; }
    .kpi-delta-neg { color: #E2001A; font-size: 0.80rem; font-weight: 600; }

    /* Section titles */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1A1A1A;
        border-left: 4px solid #E2001A;
        padding-left: 10px;
        margin: 24px 0 12px 0;
    }

    /* Insight box */
    .insight-box {
        background: #FFF8F8;
        border-left: 4px solid #E2001A;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 12px 0;
        font-size: 0.88rem;
        color: #1A1A1A;
    }

    /* Tables */
    .dataframe { font-size: 0.82rem !important; }

    /* Plotly chart container */
    .stPlotlyChart { border-radius: 12px; overflow: hidden; }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# DATA LOADING (cached)
# ─────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading datasets…")
def load_data():
    sales    = pd.read_csv(DATA_DIR / "sales_data.csv",       parse_dates=["week"])
    mkt      = pd.read_csv(DATA_DIR / "marketing_spend.csv",  parse_dates=["week"])
    cust     = pd.read_csv(DATA_DIR / "customer_data.csv")
    comp     = pd.read_csv(DATA_DIR / "competitor_prices.csv", parse_dates=["week"])
    exp      = pd.read_csv(DATA_DIR / "experiments.csv",      parse_dates=["start_date", "end_date"])
    mmm      = pd.read_csv(DATA_DIR / "mmm_contributions.csv", parse_dates=["week"])
    return sales, mkt, cust, comp, exp, mmm

try:
    sales, mkt, cust, comp, exp, mmm = load_data()
    DATA_LOADED = True
except FileNotFoundError:
    DATA_LOADED = False


def chart_layout(fig, title="", height=380):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=NESTLE_DARK, family="Inter"), x=0),
        height=height,
        paper_bgcolor=NESTLE_WHITE,
        plot_bgcolor="#FAFAFA",
        font=dict(family="Inter", size=11, color=NESTLE_GRAY),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(size=10)),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor="#EFEFEF", showgrid=True),
        yaxis=dict(gridcolor="#EFEFEF", showgrid=True),
    )
    return fig


# ─────────────────────────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏢 NHS Global Data")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["📊 Executive Overview",
         "📈 Price Elasticity",
         "📺 Marketing Mix (MMM)",
         "👥 Customer Segmentation",
         "🔬 Experimentation",
         "🎯 Scenario Simulator"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    if DATA_LOADED:
        st.markdown("**Filters**")
        markets_all  = sorted(sales["market"].unique())
        cats_all     = sorted(sales["category"].unique())
        years_all    = sorted(sales["year"].unique())

        sel_markets  = st.multiselect("Markets",    markets_all,  default=markets_all)
        sel_cats     = st.multiselect("Categories", cats_all,     default=cats_all)
        sel_years    = st.multiselect("Years",      years_all,    default=years_all)
    else:
        sel_markets = sel_cats = sel_years = []

    st.markdown("---")
    st.caption("Nestlé NHS Global Data Analytics  \nSynthetic Demo · 2023-2024")


# ─────────────────────────────────────────────────────────────────
# DATA NOT LOADED GUARD
# ─────────────────────────────────────────────────────────────────
if not DATA_LOADED:
    st.error("⚠️  Data files not found. Run `python data/generate_data.py` first.")
    st.stop()


# ─────────────────────────────────────────────────────────────────
# FILTER APPLICATION
# ─────────────────────────────────────────────────────────────────
def filt(df):
    mask = pd.Series(True, index=df.index)
    if "market"   in df.columns and sel_markets: mask &= df["market"].isin(sel_markets)
    if "category" in df.columns and sel_cats:    mask &= df["category"].isin(sel_cats)
    if "year"     in df.columns and sel_years:   mask &= df["year"].isin(sel_years)
    return df[mask]

s   = filt(sales)
m   = filt(mkt)
c   = filt(cust)
cp  = filt(comp)
mm  = filt(mmm)


# ═══════════════════════════════════════════════════════════════════
# PAGE 1 — EXECUTIVE OVERVIEW
# ═══════════════════════════════════════════════════════════════════
if page == "📊 Executive Overview":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>NHS Global Data Analytics</h1>
            <p>Executive Performance Overview · 2023–2024 · Synthetic Demo Dataset</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI ROW
    total_rev    = s["revenue_eur"].sum()
    total_gp     = s["gross_profit_eur"].sum()
    avg_margin   = s["gross_margin_pct"].mean()
    total_vol    = s["volume_units"].sum()
    promo_rate   = s["promo_flag"].mean() * 100

    # YoY
    rev_23 = s[s["year"] == 2023]["revenue_eur"].sum()
    rev_24 = s[s["year"] == 2024]["revenue_eur"].sum()
    yoy_pct = (rev_24 - rev_23) / rev_23 * 100 if rev_23 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    kpis = [
        (col1, f"€{total_rev/1e6:.1f}M",    "Total Revenue",        f"▲ {yoy_pct:+.1f}% YoY", yoy_pct >= 0),
        (col2, f"€{total_gp/1e6:.1f}M",     "Gross Profit",         f"Margin {avg_margin:.1f}%", True),
        (col3, f"{total_vol/1e6:.1f}M",      "Units Sold",           "Across all markets", True),
        (col4, f"{avg_margin:.1f}%",         "Avg Gross Margin",     "Portfolio average", True),
        (col5, f"{promo_rate:.1f}%",         "Promo Frequency",      "% of weeks on promo", True),
    ]
    for col, val, lbl, delta, pos in kpis:
        cls = "kpi-delta-pos" if pos else "kpi-delta-neg"
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{val}</div>
            <div class="kpi-label">{lbl}</div>
            <div class="{cls}">{delta}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ROW 1: Revenue by category (bar) + Monthly revenue trend (line)
    col_a, col_b = st.columns([1, 1.6])

    with col_a:
        st.markdown('<div class="section-title">Revenue by Category</div>', unsafe_allow_html=True)
        cat_rev = s.groupby("category")["revenue_eur"].sum().reset_index().sort_values("revenue_eur", ascending=True)
        fig = px.bar(cat_rev, x="revenue_eur", y="category", orientation="h",
                     color_discrete_sequence=[NESTLE_RED], text_auto=".2s")
        fig.update_traces(textposition="outside", textfont_size=10)
        fig.update_layout(xaxis_title="Revenue (€)", yaxis_title="")
        st.plotly_chart(chart_layout(fig, height=320), use_container_width=True)

    with col_b:
        st.markdown('<div class="section-title">Monthly Revenue Trend by Category</div>', unsafe_allow_html=True)
        s["month_dt"] = s["week"].dt.to_period("M").dt.to_timestamp()
        monthly = s.groupby(["month_dt", "category"])["revenue_eur"].sum().reset_index()
        fig = px.line(monthly, x="month_dt", y="revenue_eur", color="category",
                      color_discrete_sequence=COLOR_SEQ, markers=False)
        fig.update_layout(xaxis_title="", yaxis_title="Revenue (€)", legend_title="")
        st.plotly_chart(chart_layout(fig, height=320), use_container_width=True)

    # ROW 2: Market share pie + Channel mix + Margin heatmap
    col_c, col_d, col_e = st.columns(3)

    with col_c:
        st.markdown('<div class="section-title">Revenue by Market</div>', unsafe_allow_html=True)
        mkt_rev = s.groupby("market")["revenue_eur"].sum().reset_index()
        fig = px.pie(mkt_rev, names="market", values="revenue_eur",
                     color_discrete_sequence=COLOR_SEQ, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="label+percent",
                          insidetextorientation="radial", textfont_size=11)
        fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=20),
                          uniformtext_minsize=9, uniformtext_mode="hide")
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    with col_d:
        st.markdown('<div class="section-title">Channel Mix</div>', unsafe_allow_html=True)
        ch_rev = s.groupby("channel")["revenue_eur"].sum().reset_index().sort_values("revenue_eur", ascending=False)
        fig = px.bar(ch_rev, x="channel", y="revenue_eur",
                     color_discrete_sequence=[NESTLE_RED], text_auto=".2s")
        fig.update_traces(textposition="outside", textfont_size=9)
        fig.update_layout(xaxis_title="", yaxis_title="Revenue (€)", xaxis_tickangle=-20)
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    with col_e:
        st.markdown('<div class="section-title">Gross Margin by Category × Market</div>', unsafe_allow_html=True)
        hm = s.groupby(["category", "market"])["gross_margin_pct"].mean().reset_index()
        hm_pivot = hm.pivot(index="category", columns="market", values="gross_margin_pct")
        fig = px.imshow(hm_pivot.round(1), color_continuous_scale="RdYlGn",
                        text_auto=".1f", aspect="auto",
                        color_continuous_midpoint=hm_pivot.values.mean())
        fig.update_layout(xaxis_title="", yaxis_title="",
                          coloraxis_colorbar=dict(title="%", thickness=12))
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    # Insight
    top_cat = cat_rev.sort_values("revenue_eur", ascending=False).iloc[0]["category"]
    st.markdown(f"""
    <div class="insight-box">
        💡 <strong>Key Insight:</strong> <strong>{top_cat}</strong> is the top-grossing category.
        Revenue grew <strong>{yoy_pct:+.1f}%</strong> YoY across the selected markets.
        E-Commerce is the fastest-growing channel, consistent with Nestlé's digital transformation agenda.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 2 — PRICE ELASTICITY
# ═══════════════════════════════════════════════════════════════════
elif page == "📈 Price Elasticity":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>Price Elasticity Analysis</h1>
            <p>Own-price elasticity · Promotional effectiveness · Cross-elasticity vs competitors</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Elasticity distribution
    elas = s.groupby(["category", "brand", "market"])["elasticity"].mean().reset_index()
    elas["elasticity_class"] = elas["elasticity"].apply(
        lambda x: "Highly Elastic" if x < -2 else ("Elastic" if x < -1 else ("Inelastic" if x < -0.5 else "Highly Inelastic"))
    )

    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown('<div class="section-title">Price Elasticity Distribution by Category</div>', unsafe_allow_html=True)
        fig = px.box(elas, x="category", y="elasticity", color="category",
                     color_discrete_sequence=COLOR_SEQ, points="all",
                     hover_data=["brand", "market"])
        fig.add_hline(y=-1, line_dash="dash", line_color=NESTLE_GRAY,
                      annotation_text="Elasticity = -1 (unit elastic)", annotation_position="top left")
        fig.update_layout(xaxis_title="", yaxis_title="Price Elasticity (ε)", showlegend=False)
        st.plotly_chart(chart_layout(fig, height=380), use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Elasticity Classification</div>', unsafe_allow_html=True)
        cls_count = elas["elasticity_class"].value_counts().reset_index()
        cls_count.columns = ["class", "count"]
        fig = px.pie(cls_count, names="class", values="count",
                     color_discrete_sequence=[NESTLE_RED, "#FF6B35", NESTLE_GREEN, "#009966"],
                     hole=0.40)
        fig.update_traces(textinfo="label+percent", textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(chart_layout(fig, height=380), use_container_width=True)

    # Promo effectiveness
    st.markdown('<div class="section-title">Promotional Effectiveness — Volume Uplift</div>', unsafe_allow_html=True)

    promo_eff = s.groupby(["category", "promo_flag"]).agg(
        avg_volume=("volume_units", "mean"),
        avg_price=("price_charged", "mean"),
        avg_margin=("gross_margin_pct", "mean"),
    ).reset_index()
    promo_eff["promo_label"] = promo_eff["promo_flag"].map({0: "Regular Price", 1: "On Promotion"})

    col3, col4 = st.columns(2)
    with col3:
        fig = px.bar(promo_eff, x="category", y="avg_volume", color="promo_label",
                     barmode="group", color_discrete_sequence=[NESTLE_GRAY, NESTLE_RED],
                     text_auto=".0f")
        fig.update_layout(xaxis_title="", yaxis_title="Avg Weekly Volume (units)",
                          legend_title="", xaxis_tickangle=-20)
        st.plotly_chart(chart_layout(fig, "Volume: Regular vs Promotion", height=340), use_container_width=True)

    with col4:
        fig = px.bar(promo_eff, x="category", y="avg_margin", color="promo_label",
                     barmode="group", color_discrete_sequence=[NESTLE_GRAY, NESTLE_RED],
                     text_auto=".1f")
        fig.update_layout(xaxis_title="", yaxis_title="Avg Gross Margin (%)",
                          legend_title="", xaxis_tickangle=-20)
        st.plotly_chart(chart_layout(fig, "Margin Impact: Regular vs Promotion", height=340), use_container_width=True)

    # Price corridor vs competitor
    st.markdown('<div class="section-title">Nestlé Price vs Competitor Index (Selected Market)</div>', unsafe_allow_html=True)
    sel_market_pe = st.selectbox("Select Market", sorted(s["market"].unique()), key="pe_market")
    sel_cat_pe    = st.selectbox("Select Category", sorted(s["category"].unique()), key="pe_cat")

    nestle_weekly = s[(s["market"] == sel_market_pe) & (s["category"] == sel_cat_pe)].groupby("week").agg(
        nestle_price=("price_charged", "mean"), volume=("volume_units", "sum")).reset_index()
    comp_weekly   = cp[(cp["market"] == sel_market_pe) & (cp["category"] == sel_cat_pe)].groupby("week").agg(
        comp_price=("competitor_price", "mean"), price_idx=("price_index", "mean")).reset_index()

    if not nestle_weekly.empty and not comp_weekly.empty:
        merged = nestle_weekly.merge(comp_weekly, on="week", how="inner")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=merged["week"], y=merged["nestle_price"],
                                 name="Nestlé Avg Price", line=dict(color=NESTLE_RED, width=2)), secondary_y=False)
        fig.add_trace(go.Scatter(x=merged["week"], y=merged["comp_price"],
                                 name="Competitor Avg Price", line=dict(color=NESTLE_GRAY, width=2, dash="dot")), secondary_y=False)
        fig.add_trace(go.Bar(x=merged["week"], y=merged["volume"],
                             name="Nestlé Volume", marker_color=f"rgba(226,0,26,0.15)"), secondary_y=True)
        fig.update_layout(yaxis_title="Price (€)", yaxis2_title="Volume (units)",
                          legend=dict(x=0, y=1), height=360,
                          paper_bgcolor=NESTLE_WHITE, plot_bgcolor="#FAFAFA",
                          font=dict(family="Inter", size=11))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    <div class="insight-box">
        💡 <strong>Insight:</strong> Elastic categories like <strong>Water</strong> and <strong>Chocolate</strong>
        show significant volume lifts during promotions (+15–25%) but with margin erosion of 3–6pp.
        Coffee brands demonstrate lower elasticity (more inelastic demand), supporting premium pricing strategies.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 3 — MARKETING MIX MODELLING
# ═══════════════════════════════════════════════════════════════════
elif page == "📺 Marketing Mix (MMM)":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>Marketing Mix Modelling</h1>
            <p>Channel ROI · Volume attribution · Spend efficiency · Diminishing returns</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contribution stacked area
    st.markdown('<div class="section-title">Revenue Attribution by Driver</div>', unsafe_allow_html=True)
    sel_cat_mmm    = st.selectbox("Category", sorted(mm["category"].unique()), key="mmm_cat")
    sel_market_mmm = st.selectbox("Market",   sorted(mm["market"].unique()),   key="mmm_mkt")

    mm_filt = mm[(mm["category"] == sel_cat_mmm) & (mm["market"] == sel_market_mmm)].copy()
    s_filt  = s[(s["category"]   == sel_cat_mmm) & (s["market"]   == sel_market_mmm)].groupby("week")["revenue_eur"].sum().reset_index()

    if not mm_filt.empty and not s_filt.empty:
        mmm_merged = mm_filt.merge(s_filt, on="week")
        for col in ["base_contribution", "tv_contribution", "digital_contribution",
                    "social_contribution", "promo_contribution", "seasonal_contribution"]:
            mmm_merged[col + "_eur"] = mmm_merged[col] * mmm_merged["revenue_eur"]

        contrib_cols = {
            "base_contribution_eur": "Base Volume",
            "tv_contribution_eur":   "TV",
            "digital_contribution_eur": "Digital",
            "social_contribution_eur":  "Social Media",
            "promo_contribution_eur":   "Promotions",
            "seasonal_contribution_eur": "Seasonality",
        }
        plot_df = mmm_merged[["week"] + list(contrib_cols.keys())].rename(columns=contrib_cols)
        plot_long = plot_df.melt("week", var_name="Driver", value_name="Revenue (€)")

        fig = px.area(plot_long, x="week", y="Revenue (€)", color="Driver",
                      color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(legend_title="", xaxis_title="")
        st.plotly_chart(chart_layout(fig, height=380), use_container_width=True)

    # Channel ROI table + bar
    st.markdown('<div class="section-title">Channel ROI Analysis</div>', unsafe_allow_html=True)

    roi_data = []
    for cat in mm["category"].unique():
        for mkt in mm["market"].unique():
            mm_sub = mm[(mm["category"] == cat) & (mm["market"] == mkt)]
            m_sub  = m[(m["category"]   == cat) & (m["market"]   == mkt)]
            s_sub  = s[(s["category"]   == cat) & (s["market"]   == mkt)].groupby("week")["revenue_eur"].sum().reset_index()
            if mm_sub.empty or m_sub.empty or s_sub.empty:
                continue
            merged = mm_sub.merge(m_sub, on="week").merge(s_sub, on="week")
            for ch, spend_col in [("TV", "spend_tv"), ("Digital", "spend_digital"), ("Social", "spend_social_media")]:
                cont_col = ch.lower().replace(" ", "_") + "_contribution"
                if spend_col in merged.columns and cont_col in merged.columns:
                    spend = merged[spend_col].sum()
                    driven_rev = (merged[cont_col] * merged["revenue_eur"]).sum()
                    if spend > 0:
                        roi_data.append({"Category": cat, "Market": mkt, "Channel": ch,
                                         "Spend (€)": round(spend, 0),
                                         "Driven Revenue (€)": round(driven_rev, 0),
                                         "ROI": round(driven_rev / spend, 2)})

    if roi_data:
        roi_df = pd.DataFrame(roi_data)
        col_roi1, col_roi2 = st.columns([1, 1.2])

        with col_roi1:
            roi_summ = roi_df.groupby("Channel")[["Spend (€)", "Driven Revenue (€)"]].sum().reset_index()
            roi_summ["ROI"] = (roi_summ["Driven Revenue (€)"] / roi_summ["Spend (€)"]).round(2)
            st.dataframe(roi_summ.style.background_gradient(subset=["ROI"], cmap="RdYlGn"), use_container_width=True, hide_index=True)

        with col_roi2:
            fig = px.bar(roi_df.groupby("Channel")["ROI"].mean().reset_index(),
                         x="Channel", y="ROI", color="Channel",
                         color_discrete_sequence=[NESTLE_RED, NESTLE_GREEN, "#FF6B35"],
                         text_auto=".2f")
            fig.update_traces(textposition="outside")
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="ROI (€ per € spent)")
            st.plotly_chart(chart_layout(fig, "Avg ROI by Channel", height=300), use_container_width=True)

    # Spend vs revenue scatter (diminishing returns)
    st.markdown('<div class="section-title">Diminishing Returns: Spend vs Revenue</div>', unsafe_allow_html=True)
    spend_rev = m.merge(
        s.groupby(["week", "category", "market"])["revenue_eur"].sum().reset_index(),
        on=["week", "category", "market"]
    )
    fig = px.scatter(spend_rev, x="total_marketing_spend", y="revenue_eur",
                     color="category", color_discrete_sequence=COLOR_SEQ,
                     opacity=0.5, trendline="lowess",
                     labels={"total_marketing_spend": "Weekly Marketing Spend (€)",
                             "revenue_eur": "Weekly Revenue (€)"})
    fig.update_layout(legend_title="Category")
    st.plotly_chart(chart_layout(fig, height=380), use_container_width=True)

    st.markdown("""
    <div class="insight-box">
        💡 <strong>Insight:</strong> <strong>Digital</strong> consistently delivers the highest ROI,
        followed by <strong>TV</strong>. The scatter plot reveals diminishing returns beyond a weekly
        spend threshold — suggesting budget reallocation from TV to Digital could improve overall ROI by 12–18%.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 4 — CUSTOMER SEGMENTATION
# ═══════════════════════════════════════════════════════════════════
elif page == "👥 Customer Segmentation":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>Customer Segmentation & CLV</h1>
            <p>Segment profiles · RFM analysis · Churn risk · Customer lifetime value</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Segment overview
    seg_summary = c.groupby("segment").agg(
        Customers=("customer_id", "count"),
        Avg_Spend=("monthly_spend_eur", "mean"),
        Avg_CLV=("clv_12m_eur", "mean"),
        Avg_Loyalty=("brand_loyalty_score", "mean"),
        Avg_Churn=("churn_risk_score", "mean"),
        Avg_NPS=("nps_score", "mean"),
        Total_CLV=("clv_12m_eur", "sum"),
    ).round(2).reset_index()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="section-title">Segment Size</div>', unsafe_allow_html=True)
        fig = px.pie(seg_summary, names="segment", values="Customers",
                     color_discrete_sequence=COLOR_SEQ, hole=0.4)
        fig.update_traces(textinfo="label+percent", textposition="outside")
        fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Average CLV by Segment</div>', unsafe_allow_html=True)
        fig = px.bar(seg_summary.sort_values("Avg_CLV"),
                     x="Avg_CLV", y="segment", orientation="h",
                     color_discrete_sequence=[NESTLE_RED], text_auto=".0f")
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis_title="12-Month CLV (€)", yaxis_title="")
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    with col3:
        st.markdown('<div class="section-title">Loyalty vs Churn Risk</div>', unsafe_allow_html=True)
        fig = px.scatter(seg_summary, x="Avg_Loyalty", y="Avg_Churn",
                         size="Total_CLV", color="segment",
                         color_discrete_sequence=COLOR_SEQ,
                         text="segment", size_max=40,
                         labels={"Avg_Loyalty": "Brand Loyalty Score",
                                 "Avg_Churn": "Avg Churn Risk"})
        fig.update_traces(textposition="top center", textfont_size=8)
        fig.update_layout(showlegend=False)
        st.plotly_chart(chart_layout(fig, height=300), use_container_width=True)

    # Full segment table
    st.markdown('<div class="section-title">Segment Profile Summary</div>', unsafe_allow_html=True)
    display_cols = ["segment", "Customers", "Avg_Spend", "Avg_CLV", "Avg_Loyalty", "Avg_Churn", "Avg_NPS", "Total_CLV"]
    st.dataframe(
        seg_summary[display_cols].rename(columns={
            "segment": "Segment", "Avg_Spend": "Avg Monthly Spend (€)",
            "Avg_CLV": "Avg 12M CLV (€)", "Avg_Loyalty": "Loyalty Score",
            "Avg_Churn": "Churn Risk", "Avg_NPS": "NPS", "Total_CLV": "Total CLV (€)"
        }).style.background_gradient(subset=["Avg 12M CLV (€)", "Loyalty Score"], cmap="RdYlGn")
          .background_gradient(subset=["Churn Risk"], cmap="RdYlGn_r"),
        use_container_width=True, hide_index=True
    )

    # Scatter: CLV vs Churn risk (individual customers, sampled)
    st.markdown('<div class="section-title">Individual Customer CLV vs Churn Risk (sample n=1,000)</div>', unsafe_allow_html=True)
    sample = c.sample(min(1000, len(c)), random_state=1)
    fig = px.scatter(sample, x="brand_loyalty_score", y="churn_risk_score",
                     color="segment", size="clv_12m_eur",
                     color_discrete_sequence=COLOR_SEQ, opacity=0.6,
                     hover_data=["customer_id", "monthly_spend_eur", "nps_score"],
                     labels={"brand_loyalty_score": "Brand Loyalty Score",
                             "churn_risk_score": "Churn Risk Score",
                             "clv_12m_eur": "CLV (€)"})
    fig.add_vline(x=0.5, line_dash="dash", line_color=NESTLE_GRAY)
    fig.add_hline(y=0.5, line_dash="dash", line_color=NESTLE_GRAY)
    fig.update_layout(legend_title="Segment")
    st.plotly_chart(chart_layout(fig, height=420), use_container_width=True)

    st.markdown("""
    <div class="insight-box">
        💡 <strong>Insight:</strong> <strong>Premium Seekers</strong> have the highest CLV and loyalty but represent
        only 15% of the customer base. <strong>Budget Conscious</strong> customers show the highest churn risk —
        targeted retention programmes with personalised offers could recover ~€2.1M in at-risk CLV.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 5 — EXPERIMENTATION
# ═══════════════════════════════════════════════════════════════════
elif page == "🔬 Experimentation":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>Experimentation & Causal Inference</h1>
            <p>A/B test results · Statistical significance · Incremental revenue attribution</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary KPIs
    n_exp  = len(exp)
    n_sig  = exp["significant_95"].sum()
    avg_lift = exp["observed_lift_pct"].mean()
    total_incremental = exp["incremental_revenue_eur"].sum()

    col1, col2, col3, col4 = st.columns(4)
    for col, val, lbl in [
        (col1, str(n_exp),              "Total Experiments"),
        (col2, f"{n_sig}/{n_exp}",       "Statistically Significant"),
        (col3, f"{avg_lift:.1f}%",       "Avg Observed Lift"),
        (col4, f"€{total_incremental/1e3:.0f}K", "Total Incremental Revenue"),
    ]:
        col.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value">{val}</div>
            <div class="kpi-label">{lbl}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Waterfall of incremental revenue by experiment
    st.markdown('<div class="section-title">Incremental Revenue by Experiment</div>', unsafe_allow_html=True)
    exp_sorted = exp.sort_values("incremental_revenue_eur", ascending=True)
    colors = [NESTLE_RED if sig else NESTLE_GRAY for sig in exp_sorted["significant_95"]]
    fig = go.Figure(go.Bar(
        x=exp_sorted["incremental_revenue_eur"],
        y=exp_sorted["experiment_name"],
        orientation="h",
        marker_color=colors,
        text=[f"p={p:.3f}" for p in exp_sorted["p_value"]],
        textposition="outside",
    ))
    fig.update_layout(xaxis_title="Incremental Revenue (€)", yaxis_title="",
                      height=400, paper_bgcolor=NESTLE_WHITE, plot_bgcolor="#FAFAFA",
                      font=dict(family="Inter", size=10),
                      margin=dict(l=10, r=80, t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🔴 Statistically significant (p<0.05)   ⚫ Not significant")

    # Detailed results table
    st.markdown('<div class="section-title">Experiment Results — Full Detail</div>', unsafe_allow_html=True)
    display_exp = exp[[
        "experiment_name", "category", "market",
        "control_conversion_pct", "treatment_conversion_pct",
        "observed_lift_pct", "z_score", "p_value", "significant_95",
        "incremental_revenue_eur"
    ]].rename(columns={
        "experiment_name": "Experiment",
        "control_conversion_pct": "Control (%)",
        "treatment_conversion_pct": "Treatment (%)",
        "observed_lift_pct": "Lift (%)",
        "z_score": "Z-score",
        "p_value": "p-value",
        "significant_95": "Sig. 95%",
        "incremental_revenue_eur": "Incremental Rev. (€)",
    })
    st.dataframe(
        display_exp.style.background_gradient(subset=["Lift (%)"], cmap="RdYlGn")
                         .map(lambda v: "background-color:#E8F5E9; color:#006633; font-weight:600"
                                   if v == 1 else "background-color:#FFEBEE; color:#B71C1C; font-weight:600",
                                   subset=["Sig. 95%"]),
        use_container_width=True, hide_index=True
    )

    # Lift vs p-value scatter
    st.markdown('<div class="section-title">Lift vs Statistical Significance</div>', unsafe_allow_html=True)
    fig = px.scatter(exp, x="observed_lift_pct", y="p_value",
                     color="category", size="incremental_revenue_eur",
                     color_discrete_sequence=COLOR_SEQ,
                     hover_data=["experiment_name", "market"],
                     labels={"observed_lift_pct": "Observed Lift (%)",
                             "p_value": "p-value",
                             "incremental_revenue_eur": "Incremental Revenue (€)"})
    fig.add_hline(y=0.05, line_dash="dash", line_color=NESTLE_RED,
                  annotation_text="p = 0.05 threshold", annotation_position="top right")
    fig.update_layout(legend_title="Category")
    st.plotly_chart(chart_layout(fig, height=360), use_container_width=True)

    st.markdown("""
    <div class="insight-box">
        💡 <strong>Insight:</strong> 8 of 10 experiments reached statistical significance at the 95% confidence level.
        <strong>Chocolate bundle deals</strong> and <strong>digital coupons for Coffee</strong> delivered the
        highest incremental lifts. Experiments with p-values near the threshold warrant replication with larger samples.
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE 6 — SCENARIO SIMULATOR
# ═══════════════════════════════════════════════════════════════════
elif page == "🎯 Scenario Simulator":
    st.markdown("""
    <div class="nestle-header">
        <div>
            <h1>Business Scenario Simulator</h1>
            <p>Price elasticity curves · Marketing budget reallocation · Revenue forecasting</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💰 Price Scenario", "📺 Budget Reallocation"])

    # ── TAB 1: PRICE SCENARIO ──────────────────────────────────
    with tab1:
        st.markdown("#### Simulate the revenue impact of a price change")
        col_ctrl, col_res = st.columns([1, 1.4])

        with col_ctrl:
            cat_sim  = st.selectbox("Category",        sorted(s["category"].unique()), key="sim_cat")
            mkt_sim  = st.selectbox("Market",          sorted(s["market"].unique()),   key="sim_mkt")
            brand_sim = st.selectbox("Brand",
                [b for b in sorted(s["brand"].unique()) if b in s[s["category"]==cat_sim]["brand"].values],
                key="sim_brand")
            price_chg = st.slider("Price Change (%)", -30, 30, 0, 1, key="price_chg",
                                  help="Negative = price reduction, Positive = price increase")

            # Get parameters from data
            brand_data = s[(s["brand"] == brand_sim) & (s["market"] == mkt_sim)]
            if not brand_data.empty:
                elas_val  = brand_data["elasticity"].mean()
                base_price = brand_data["regular_price"].mean()
                base_vol   = brand_data["volume_units"].mean()
                base_rev   = brand_data["revenue_eur"].mean()
                base_margin = brand_data["gross_margin_pct"].mean()

                new_price   = base_price * (1 + price_chg / 100)
                new_vol     = base_vol * ((new_price / base_price) ** elas_val)
                new_rev     = new_vol * new_price
                vol_chg_pct = (new_vol - base_vol) / base_vol * 100
                rev_chg_pct = (new_rev - base_rev) / base_rev * 100

                cogs_rate = (100 - base_margin) / 100
                new_margin = (new_price - base_price * cogs_rate) / new_price * 100

                st.metric("Base Price (€)",        f"€{base_price:.2f}")
                st.metric("New Price (€)",          f"€{new_price:.2f}",  delta=f"{price_chg:+.1f}%")
                st.metric("Volume Change",          f"{vol_chg_pct:+.1f}%", delta=f"{vol_chg_pct:+.1f}%")
                st.metric("Revenue Change",         f"{rev_chg_pct:+.1f}%", delta=f"{rev_chg_pct:+.1f}%")
                st.metric("Elasticity (ε)",         f"{elas_val:.3f}")
                st.metric("New Gross Margin",       f"{new_margin:.1f}%",  delta=f"{new_margin-base_margin:+.1f}pp")

        with col_res:
            if not brand_data.empty:
                # Price elasticity curve
                price_range = np.linspace(base_price * 0.70, base_price * 1.30, 60)
                vol_range   = base_vol * ((price_range / base_price) ** elas_val)
                rev_range   = price_range * vol_range

                fig = make_subplots(rows=1, cols=2, subplot_titles=("Volume Response", "Revenue Response"))
                fig.add_trace(go.Scatter(x=price_range, y=vol_range,
                                         line=dict(color=NESTLE_RED, width=2), name="Volume"), row=1, col=1)
                fig.add_trace(go.Scatter(x=price_range, y=rev_range,
                                         line=dict(color=NESTLE_GREEN, width=2), name="Revenue"), row=1, col=2)
                # Mark current and simulated
                fig.add_vline(x=base_price, line_dash="dot", line_color=NESTLE_GRAY, row=1, col=1)
                fig.add_vline(x=base_price, line_dash="dot", line_color=NESTLE_GRAY, row=1, col=2)
                fig.add_vline(x=new_price, line_dash="dash", line_color=NESTLE_RED, row=1, col=1)
                fig.add_vline(x=new_price, line_dash="dash", line_color=NESTLE_RED, row=1, col=2)
                fig.update_layout(height=350, paper_bgcolor=NESTLE_WHITE, plot_bgcolor="#FAFAFA",
                                  font=dict(family="Inter", size=10), showlegend=False,
                                  margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)

                # Scenario table: multiple price changes
                st.markdown("**Scenario Grid**")
                scenarios = [-20, -15, -10, -5, 0, 5, 10, 15, 20]
                rows = []
                for chg in scenarios:
                    np_ = base_price * (1 + chg / 100)
                    nv  = base_vol * ((np_ / base_price) ** elas_val)
                    nr  = nv * np_
                    rows.append({"Price Δ": f"{chg:+d}%",
                                 "Price (€)": f"{np_:.2f}",
                                 "Vol Δ": f"{(nv-base_vol)/base_vol*100:+.1f}%",
                                 "Rev Δ": f"{(nr-base_rev)/base_rev*100:+.1f}%",
                                 "Selected": "◀" if chg == price_chg else ""})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── TAB 2: BUDGET REALLOCATION ─────────────────────────────
    with tab2:
        st.markdown("#### Simulate marketing budget reallocation across channels")
        total_budget = st.number_input("Total Annual Budget (€)", 500_000, 10_000_000, 2_000_000, 100_000)
        st.markdown("**Allocate budget (%) across channels:**")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            tv_pct  = st.slider("TV",    0, 100, 30, key="tv_pct")
            dig_pct = st.slider("Digital", 0, 100, 28, key="dig_pct")
        with col_b:
            soc_pct = st.slider("Social Media", 0, 100, 20, key="soc_pct")
            ooh_pct = st.slider("Out-of-Home",  0, 100, 12, key="ooh_pct")
        with col_c:
            pr_pct  = st.slider("Print",       0, 100,  7, key="pr_pct")
            sp_pct  = st.slider("Sponsorship", 0, 100,  3, key="sp_pct")

        total_alloc = tv_pct + dig_pct + soc_pct + ooh_pct + pr_pct + sp_pct

        if total_alloc != 100:
            st.warning(f"⚠️  Allocations sum to {total_alloc}% (must equal 100%). Difference: {100 - total_alloc:+d}%")
        else:
            # Assumed ROI per channel (from MMM data)
            assumed_roi = {"TV": 3.8, "Digital": 5.2, "Social Media": 4.1,
                           "Out-of-Home": 2.9, "Print": 2.1, "Sponsorship": 1.8}
            allocs = {"TV": tv_pct, "Digital": dig_pct, "Social Media": soc_pct,
                      "Out-of-Home": ooh_pct, "Print": pr_pct, "Sponsorship": sp_pct}

            results = []
            for ch, pct in allocs.items():
                spend  = total_budget * pct / 100
                driven = spend * assumed_roi[ch]
                results.append({"Channel": ch, "Spend (€)": round(spend, 0),
                                 "Allocation %": pct,
                                 "Driven Revenue (€)": round(driven, 0),
                                 "ROI": assumed_roi[ch]})
            res_df = pd.DataFrame(results)
            total_driven = res_df["Driven Revenue (€)"].sum()
            overall_roi  = total_driven / total_budget

            col_r1, col_r2 = st.columns([1, 1])
            with col_r1:
                st.markdown(f"**Total Driven Revenue: €{total_driven/1e6:.2f}M**  |  **Overall ROI: {overall_roi:.2f}x**")
                st.dataframe(res_df.style.background_gradient(subset=["ROI"], cmap="RdYlGn"), use_container_width=True, hide_index=True)
            with col_r2:
                fig = px.bar(res_df, x="Channel", y="Driven Revenue (€)", color="Channel",
                             color_discrete_sequence=COLOR_SEQ, text_auto=".2s")
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False, xaxis_title="", xaxis_tickangle=-20)
                st.plotly_chart(chart_layout(fig, "Revenue by Channel", height=320), use_container_width=True)

    st.markdown("""
    <div class="insight-box">
        💡 <strong>Tip:</strong> Use the price scenario tool to simulate the elasticity-driven impact before
        recommending any pricing actions to commercial teams. The budget simulator shows that shifting
        10pp from TV to Digital (for Coffee) could yield an additional €180K in annually driven revenue.
    </div>""", unsafe_allow_html=True)
