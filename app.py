import streamlit as st
import pandas as pd
import plotly.express as px


# 1. PAGE CONFIG & THEME


st.set_page_config(
    page_title="Karnataka Assembly 2023 – Election Analytics",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        color: white;
    }
    h1, h2, h3, h4 {
        color: #fafafa;
    }
    .stMetricLabel {
        color: #d0d0d0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOAD DATA

CSV_FILE_NAME = "karnataka_assembly_2023.csv"

@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE_NAME)

    required = [
        "Constituency_ID",
        "Constituency_Name",
        "Winner_Name",
        "Winner_Party",
        "Winner",
        "Region",
        "Margin",
        "Turnout_Percentage",
        "Seats"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"CSV is missing required columns: {missing}")
        st.stop()

    # Ensure numeric fields are numeric
    df["Margin"] = pd.to_numeric(df["Margin"], errors="coerce").fillna(0).astype(int)
    df["Turnout_Percentage"] = pd.to_numeric(df["Turnout_Percentage"], errors="coerce").fillna(72.0)
    df["Seats"] = pd.to_numeric(df["Seats"], errors="coerce").fillna(1).astype(int)

    # Normalize Winner bucket once more just to be safe
    def norm_party(p):
        p = str(p).upper().strip()
        if p == "INC" or "CONGRESS" in p:
            return "INC"
        if p == "BJP" or "BHARATIYA JANATA" in p:
            return "BJP"
        if p.startswith("JD") or "JANATA DAL" in p:
            return "JDS"
        return "Others"

    df["Winner"] = df["Winner"].apply(norm_party)
    return df

df = load_data()

color_map = {
    "INC": "#1F77B4",
    "BJP": "#FF7F0E",
    "JDS": "#2CA02C",
    "Others": "#7F7F7F",
}

# 3. SIDEBAR & FILTERS

st.sidebar.title("🗳️ Karnataka 2023 Analytics")
st.sidebar.markdown("Constituency-wise analysis of the **2023 Assembly result**.")

view_mode = st.sidebar.radio(
    "Navigate to:",
    ["Executive Summary", "Regional Deep-Dive", "Constituency Analysis"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Global Filters")

region_filter = st.sidebar.multiselect(
    "Filter by Region",
    options=sorted(df["Region"].unique()),
    default=sorted(df["Region"].unique())
)

party_filter = st.sidebar.multiselect(
    "Filter by Winning Party (Bucket)",
    options=["INC", "BJP", "JDS", "Others"],
    default=["INC", "BJP", "JDS", "Others"]
)

turnout_min, turnout_max = st.sidebar.slider(
    "Voter Turnout Range (%)",
    min_value=0.0,
    max_value=100.0,
    value=(0.0, 100.0),
    step=0.5
)

st.sidebar.markdown("---")
st.sidebar.info(
    "📌 Data: Karnataka Assembly Election 2023 (real winners, parties, and derived metrics)."
)

filtered_df = df[
    df["Region"].isin(region_filter)
    & df["Winner"].isin(party_filter)
    & df["Turnout_Percentage"].between(turnout_min, turnout_max)
]

if filtered_df.empty:
    st.error("No data matches the current filters. Relax the filters in the sidebar.")
    st.stop()

# 4. AGGREGATIONS

party_counts_state = df["Winner"].value_counts().sort_index()
total_seats_state = len(df)
majority_mark = (total_seats_state // 2) + 1
winner_party_state = party_counts_state.idxmax()

party_counts_filtered = filtered_df["Winner"].value_counts().sort_index()
total_seats_filtered = len(filtered_df)

# 5. VIEWS

if view_mode == "Executive Summary":
    st.title("🛡️ Executive Summary: Karnataka Mandate 2023")
    st.caption("Congress formed the government in 2023. This dashboard reflects the full mandate.")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Government Formed By (Statewide)",
        winner_party_state,
        "Majority" if party_counts_state[winner_party_state] >= majority_mark else "Hung Assembly",
    )

    c2.metric("INC Seats (Statewide)", party_counts_state.get("INC", 0))
    c3.metric("BJP Seats (Statewide)", party_counts_state.get("BJP", 0))
    c4.metric("Avg Turnout (Filtered View)", f"{filtered_df['Turnout_Percentage'].mean():.2f}%")

    st.markdown("---")

    st.subheader("🗺️ Seat Matrix by Region (Filtered Scope)")
    regional_summary = (
        filtered_df
        .groupby(["Region", "Winner"])["Seats"]
        .sum()
        .reset_index()
        .pivot(index="Region", columns="Winner", values="Seats")
        .fillna(0)
        .astype(int)
        .sort_index()
    )
    regional_summary["Total_Seats"] = regional_summary.sum(axis=1)
    st.dataframe(regional_summary, use_container_width=True)

    st.markdown("---")

    c1, c2 = st.columns([1.5, 1])

    with c1:
        st.subheader("🏛️ Assembly Composition (Sunburst) – Filtered")
        fig_sun = px.sunburst(
            filtered_df,
            path=["Region", "Winner"],
            values="Seats",
            color="Winner",
            color_discrete_map=color_map,
        )
        st.plotly_chart(fig_sun, use_container_width=True)

    with c2:
        st.subheader("📊 Seat Share Donut – Filtered")
        fig_pie = px.pie(
            names=party_counts_filtered.index,
            values=party_counts_filtered.values,
            color=party_counts_filtered.index,
            color_discrete_map=color_map,
            hole=0.55,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("🎯 Statewide vs Filtered Seat Share")
    comp_df = pd.DataFrame({
        "Party": ["INC", "BJP", "JDS", "Others"],
        "Statewide_Seats": [party_counts_state.get(p, 0) for p in ["INC", "BJP", "JDS", "Others"]],
        "Filtered_Seats": [party_counts_filtered.get(p, 0) for p in ["INC", "BJP", "JDS", "Others"]],
    })
    comp_df["Statewide_%"] = comp_df["Statewide_Seats"] / total_seats_state * 100
    comp_df["Filtered_%"] = comp_df["Filtered_Seats"] / total_seats_filtered * 100

    comp_long = comp_df.melt(
        id_vars="Party",
        value_vars=["Statewide_%", "Filtered_%"],
        var_name="Scope",
        value_name="Seat_Share_%"
    )
    comp_long["Scope"] = comp_long["Scope"].replace({
        "Statewide_%": "Statewide",
        "Filtered_%": "Filtered View",
    })

    fig_comp = px.bar(
        comp_long,
        x="Party",
        y="Seat_Share_%",
        color="Scope",
        barmode="group",
        text_auto=".1f",
    )
    fig_comp.update_yaxes(title="Seat Share (%)", range=[0, 100])
    st.plotly_chart(fig_comp, use_container_width=True)


elif view_mode == "Regional Deep-Dive":
    st.title("📍 Regional Performance Deep-Dive")

    regional_options = sorted(filtered_df["Region"].unique())
    selected_region = st.selectbox("Select Region", regional_options)
    regional_df = filtered_df[filtered_df["Region"] == selected_region]

    c1, c2 = st.columns(2)

    with c1:
        st.subheader(f"Party Strength in {selected_region}")
        fig_reg_bar = px.histogram(
            regional_df,
            x="Winner",
            color="Winner",
            color_discrete_map=color_map,
            text_auto=True,
        )
        fig_reg_bar.update_layout(
            xaxis_title="Party (Bucket)",
            yaxis_title="Seats Won",
        )
        st.plotly_chart(fig_reg_bar, use_container_width=True)

    with c2:
        st.subheader("Victory Margin Distribution")
        fig_box = px.box(
            regional_df,
            x="Winner",
            y="Margin",
            color="Winner",
            color_discrete_map=color_map,
            points="all",
        )
        fig_box.update_yaxes(title="Victory Margin (Votes)")
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")
    st.subheader(f"🔎 Constituency List – {selected_region}")
    st.dataframe(
        regional_df[
            ["Constituency_ID", "Constituency_Name", "Winner_Name", "Winner_Party", "Winner", "Margin", "Turnout_Percentage"]
        ].sort_values("Margin", ascending=False),
        use_container_width=True,
    )


elif view_mode == "Constituency Analysis":
    st.title("🔍 Micro-Analysis: Safe vs Swing Seats")

    fig_scatter = px.scatter(
        filtered_df,
        x="Turnout_Percentage",
        y="Margin",
        color="Winner",
        size="Margin",
        hover_name="Constituency_Name",
        hover_data={"Winner_Name": True, "Winner_Party": True},
        color_discrete_map=color_map,
        labels={
            "Turnout_Percentage": "Voter Turnout (%)",
            "Margin": "Victory Margin (Votes)",
        },
        title="Victory Margin vs Voter Turnout",
    )

    close_threshold = 2000
    turnout_mid = filtered_df["Turnout_Percentage"].median()

    fig_scatter.add_hline(
        y=close_threshold,
        line_dash="dash",
        annotation_text=f"Close Fight (< {close_threshold} votes)",
        annotation_position="top left",
    )
    fig_scatter.add_vline(
        x=turnout_mid,
        line_dash="dot",
        annotation_text=f"Median Turnout ({turnout_mid:.1f}%)",
        annotation_position="bottom right",
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

    swing_seats = filtered_df[filtered_df["Margin"] < close_threshold]
    safe_seats = filtered_df[filtered_df["Margin"] >= close_threshold]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Seats (Filtered)", len(filtered_df))
    c2.metric("Close Contests (<2000)", len(swing_seats))
    c3.metric("Safe Seats (≥2000)", len(safe_seats))

    st.markdown("---")
    st.subheader("📋 Raw Data Explorer (Filtered)")
    with st.expander("Click to view full filtered dataset"):
        st.dataframe(
            filtered_df.sort_values("Margin", ascending=True),
            use_container_width=True,
        )

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered dataset as CSV",
        data=csv,
        file_name="karnataka_2023_filtered_view.csv",
        mime="text/csv",
    )

