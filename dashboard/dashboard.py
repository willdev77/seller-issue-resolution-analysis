# =========================
# Seller Issue Dashboard - Executive v2
# =========================

import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(
    layout="wide",
    page_title="Support Ticket Resolution Dashboard",
    page_icon="📊"
)

PRIMARY_COLOR = "#4C78A8"
SECONDARY_COLOR = "#F58518"
SUCCESS_COLOR = "#54A24B"
DANGER_COLOR = "#E45756"
WARNING_COLOR = "#ECA82C"

PORTFOLIO_MODE = True
SLA_DAYS = 5

# -------------------------
# CSS / PRINT
# -------------------------
st.markdown("""
<style>
@media print {
    section[data-testid="stSidebar"] {
        display: none !important;
    }

    header, footer {
        display: none !important;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    body {
        zoom: 80%;
    }

    @page {
        size: A4;
        margin: 10mm;
    }
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1rem;
}

.element-container {
    margin-bottom: 0.4rem !important;
}

h1, h2, h3 {
    margin-bottom: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# LOAD DATA
# -------------------------
df = pd.read_csv("data/processed/seller_issues_clean.csv")

# -------------------------
# DATA PREP
# -------------------------
df["activity_date"] = pd.to_datetime(df["activity_date"], errors="coerce")
df = df.dropna(subset=["activity_date"]).copy()

if "resolution_time_days" in df.columns:
    df["resolution_time_days"] = pd.to_numeric(df["resolution_time_days"], errors="coerce")

df["alias"] = df["alias"].fillna("Unknown")
df["status"] = df["status"].fillna("Unknown")
df["category_tag"] = df["category_tag"].fillna("Unknown")

# -------------------------
# ANONYMIZATION FOR PORTFOLIO
# -------------------------
if PORTFOLIO_MODE:
    # Mask analyst names
    unique_aliases = sorted(df["alias"].dropna().unique())
    alias_map = {
        original_name: f"Analyst {i:02d}"
        for i, original_name in enumerate(unique_aliases, start=1)
    }
    df["alias"] = df["alias"].map(alias_map)

    # Mask categories
    unique_categories = sorted(df["category_tag"].dropna().unique())
    category_map = {
        original_category: f"Category {i:02d}"
        for i, original_category in enumerate(unique_categories, start=1)
    }
    df["category_tag"] = df["category_tag"].map(category_map)


min_date = df["activity_date"].min().date()
max_date = df["activity_date"].max().date()


# -------------------------
# SIDEBAR FILTERS
# -------------------------
st.sidebar.header("Filters")

analyst_options = sorted(df["alias"].dropna().unique())
category_options = sorted(df["category_tag"].dropna().unique())
status_options = sorted(df["status"].dropna().unique())

analyst_filter = st.sidebar.multiselect(
    "Select Analyst",
    analyst_options,
    default=analyst_options
)

category_filter = st.sidebar.multiselect(
    "Select Category",
    category_options,
    default=category_options
)

status_filter = st.sidebar.multiselect(
    "Select Status",
    status_options,
    default=status_options
)

date_range = st.sidebar.date_input(
    "Select Period",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

if len(date_range) != 2:
    st.warning("Selecione um intervalo de datas válido.")
    st.stop()

start_date, end_date = date_range

# -------------------------
# PERIOD CALCULATION
# -------------------------
period_days = (end_date - start_date).days + 1
previous_end = start_date - pd.Timedelta(days=1)
previous_start = previous_end - pd.Timedelta(days=period_days - 1)

# -------------------------
# FILTERED DATA - CURRENT
# -------------------------
filtered_df = df[
    (df["alias"].isin(analyst_filter)) &
    (df["category_tag"].isin(category_filter)) &
    (df["status"].isin(status_filter)) &
    (df["activity_date"].dt.date >= start_date) &
    (df["activity_date"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

filtered_df["sla_status"] = filtered_df["resolution_time_days"].apply(
    lambda x: "Within SLA" if pd.notnull(x) and x <= SLA_DAYS else "Outside SLA"
)

# -------------------------
# FILTERED DATA - PREVIOUS PERIOD
# -------------------------
previous_df = df[
    (df["alias"].isin(analyst_filter)) &
    (df["category_tag"].isin(category_filter)) &
    (df["status"].isin(status_filter)) &
    (df["activity_date"].dt.date >= previous_start) &
    (df["activity_date"].dt.date <= previous_end)
].copy()

if not previous_df.empty:
    previous_df["sla_status"] = previous_df["resolution_time_days"].apply(
        lambda x: "Within SLA" if pd.notnull(x) and x <= SLA_DAYS else "Outside SLA"
    )

# -------------------------
# KPI FUNCTION
# -------------------------
def calculate_kpis(dataframe):
    total_tickets = len(dataframe)

    resolved_tickets = (dataframe['status'] == 'COMPLETED').sum() if total_tickets > 0 else 0
    open_tickets =  (dataframe['status'] == "WORK IN PROGRESS").sum() if total_tickets > 0 else 0

    resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
    avg_resolution = dataframe['resolution_time_days'].mean()
    sla_compliance = (dataframe['sla_status'] == 'Within SLA').mean() * 100 if total_tickets > 0 else 0
    pending_rate = (open_tickets / total_tickets * 100) if total_tickets > 0 else 0

    return {
        "total_tickets": total_tickets,
        "resolved_tickets":resolved_tickets,
        "open_tickets": open_tickets,
        "resolution_rate":resolution_rate,
        "avg_resolution" : avg_resolution,
        "sla_compliance":sla_compliance,
        "pending_rate": pending_rate
    }
current_kpis = calculate_kpis(filtered_df)
previous_kpis = calculate_kpis(previous_df) if not previous_df.empty else None

# -------------------------
# DELTA FORMATTERS
# -------------------------
def delta_value(current,previous):
    if previous is None:
        return None
    return current - previous

def delta_text_pp(current, previous):
    if previous is None:
        return "N/A"
    diff = current - previous
    return f"{diff:+.1f} pp"

def delta_text_num(current, previous):
    if previous is None:
        return "N/A"
    diff = current - previous
    return f"{diff:+.0f}"

def delta_text_days(current, previous):
    if previous is None:
        return "N/A"
    diff = current - previous
    return f"{diff:+.1f} d"

# -------------------------
# TITLE
# -------------------------
st.title("Support Ticket Resolution Dashboard")
st.caption(
    f"Periodo analisado: {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')} "
    f"Comparação: {previous_start.strftime('%d/%m/%Y')} → {previous_end.strftime('%d/%m/%Y')}"
)
# -------------------------
# KPI CALCULATIONS
# -------------------------
total_tickets = len(filtered_df)
resolved_tickets = (filtered_df['status'] == 'COMPLETED').sum()
open_tickets =  (filtered_df['status'] == "WORK IN PROGRESS").sum()

resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
avg_resolution = filtered_df['resolution_time_days'].mean()
sla_compliance = (filtered_df['sla_status'] == 'Within SLA').mean() * 100 if total_tickets > 0 else 0
pending_rate = (open_tickets / total_tickets * 100) if total_tickets > 0 else 0

# -------------------------
# KPI ROW
# -------------------------
k1, k2, k3, k4, k5 = st.columns(5)

if previous_kpis is not None:
    prev_total = previous_kpis["total_tickets"]
    prev_resolution = previous_kpis["resolution_rate"]
    prev_avg_time = previous_kpis["avg_resolution"]
    prev_open = previous_kpis["open_tickets"]
    prev_sla = previous_kpis["sla_compliance"]
else:
    prev_total = None
    prev_resolution = None
    prev_avg_time = None
    prev_open = None
    prev_sla = None

k1.metric("📦 Total Tickets", 
          f"{current_kpis["total_tickets"]}",
          delta_text_num(current_kpis['total_tickets'],prev_total)
)

k2.metric("✅ Resolution Rate", 
          f"{current_kpis["resolution_rate"]:.1f}%",
          delta_text_pp(current_kpis['resolution_rate'], prev_resolution)
)
k3.metric("⏱ Avg Resolutuion Time", 
          f"{current_kpis["avg_resolution"]:.1f}d" if pd.notnull(current_kpis['avg_resolution']) else "N/A",
          delta_text_days(current_kpis['avg_resolution'], prev_avg_time)
)
k4.metric("⚠️ Open Tickets", 
          f"{current_kpis["open_tickets"]}",
          delta_text_num(current_kpis["open_tickets"], prev_open)
)
k5.metric("🎯 SLA Compliance", 
          f"{current_kpis["sla_compliance"]:.1f}%",
          delta_text_pp(current_kpis['sla_compliance'], prev_sla)
)

st.divider()

# -------------------------
# EXECUTIVE SUMMARY
# -------------------------
category_df = filtered_df['category_tag'].value_counts().reset_index()
category_df.columns = ['category', 'tickets']

top_category = category_df.iloc[0]['category'] if not category_df.empty else "N/A"

tickets_by_analyst = filtered_df['alias'].value_counts().reset_index()
tickets_by_analyst.columns = ['analyst', 'tickets']

resolution_by_analyst = (
    filtered_df.groupby("alias", as_index=False)["resolution_time_days"]
    .mean()
    .rename(columns={"resolution_time_days": "avg_resolution"})
)

performance_df = (
    filtered_df.groupby("alias", as_index=False)
    .agg(
        tickets=("activity_id", "count"),
        avg_resolution=("resolution_time_days", "mean")
    )
)

best_analyst = (
    performance_df.sort_values("avg_resolution", ascending=True).iloc[0]["alias"]
    if not performance_df.empty else "N/A"
)

top_volume_analyst = (
    performance_df.sort_values("tickets", ascending=False).iloc[0]["alias"]
    if not performance_df.empty else 'N/A'
)


st.markdown("## 🧠 Executive Summary")

sumary_col1, sumary_col2 = st.columns([2.2, 1])

with sumary_col1:
    st.markdown(f"""
**Resumo do periodo**
    - Foram analisados **{current_kpis["total_tickets"]} tickets** no periodo selecionado.
    - A taxa de resolução foi de **{current_kpis["resolution_rate"]:.1f}%**, com **{resolved_tickets} tickets concluidos**.
    - O tempe medio de resolução foi de **{current_kpis["avg_resolution"]:.1f} dias**.
    - O cumprimento de SLA ficou em **{current_kpis["sla_compliance"]:.1f}%**.
    - A categoria com maior volume foi **{top_category}**.
    -**{best_analyst}** apresentou o menor tempo medio de resolução.
    -**{top_volume_analyst}** concentrou o maior volume de tickets.
""")

with sumary_col2:
    if current_kpis["sla_compliance"] >= 85:
        st.success("Operação saudavel: o SLA está em bom nivel no periodo.")
    elif current_kpis["sla_compliance"] >= 70:
        st.warning("Atenção: o SLA está em nivel intermediario e merece monitoramento.")
    else:
        st.error("Risco operacional: o SLA está baixo e indica necessidade de ação imediata.")
    
    if current_kpis["pending_rate"] > 20:
        st.warning(f"Backlog relevante:{current_kpis["pending_rate"]:.1f}% dos tickets ainda estão abertos.")
    else: 
        st.info(f"Backlog controlado: {current_kpis["pending_rate"]:.1f}% dos tickets permancem em aberto.")

st.divider()
# -------------------------
# VISUAL ALERTS VS PREVIOUS PERIOD
# -------------------------
st.markdown("## 🚨 Alerts vs Previous Period")

a1, a2, a3 = st.columns(3)

if previous_kpis is None or previous_df.empty:
    st.info("Não há dados suficientes no período anterior para comparação.")
else:
    resolution_rate_diff = current_kpis["resolution_rate"] - previous_kpis["resolution_rate"]
    avg_resolution_diff = current_kpis["avg_resolution"] - previous_kpis['avg_resolution']
    sla_diff = current_kpis['sla_compliance'] - previous_kpis['sla_compliance']

    with a1:
        if resolution_rate_diff > 0:
            st.success(f"Resolution Rate melhorou em {resolution_rate_diff:.1f} pp.")
        elif resolution_rate_diff < 0:
            st.error(f"Resolution Rate piorou em {abs(resolution_rate_diff):.1f} pp.")
        else:
            st.info("Resolution Rate está estável.")

    with a2:
        if avg_resolution_diff < 0:
            st.success(f"Avg Resolution Time melhorou em {abs(avg_resolution_diff):.1f} dias.")
        elif avg_resolution_diff > 0:
            st.error(f"Avg Resolution Time piorou em {avg_resolution_diff:.1f} dias.")
        else:
            st.info("Avg Resolution Time está estável.")
    with a3:
        if sla_diff > 0:
            st.success(f"SLA Compliance melhorou em {sla_diff:.1f} pp.")
        elif sla_diff < 0:
            st.error(f"SLA Compliance piorou em {abs(sla_diff):.1f} pp.")
        else:
            st.info("SLA Compliance está estável.")
st.divider()        

# -------------------------
# OPERATIONAL HEALTH
# -------------------------
st.markdown("## 📊 Operational Health")

c1, c2,c3 = st.columns([1.8, 1, 1.2])

with c1:
    tickets_time = (
        filtered_df.groupby(pd.Grouper(key='activity_date', freq='D'))['activity_id']
        .count()
        .reset_index()
        .rename(columns={'activity_id':'tickets'})
    )

    fig_time = px.line(
        tickets_time,
        x='activity_date',
        y='tickets',
        title='Daily Ticket Volume',
        markers=True
    )
    fig_time.update_traces(line=dict(color=PRIMARY_COLOR))
    fig_time.update_layout(
        xaxis_title='Date',
        yaxis_title='Tickets',
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        height=320
    )
    st.plotly_chart(fig_time, use_container_width=True)

with c2:
    sla_df = filtered_df['sla_status'].value_counts().reset_index()
    sla_df.columns = ['status', 'count']

    fig_sla = px.pie(
    sla_df,
    names='status',
    values = 'count',
    title='SLA Compliance',
    hole=0.55,
    )
    fig_sla.update_traces(
    marker=dict(colors=[PRIMARY_COLOR, DANGER_COLOR])
    )
    fig_sla.update_layout(height = 320)
    st.plotly_chart(fig_sla, use_container_width=True)

with c3:
    top_categories = category_df.head(8).sort_values("tickets", ascending=True)

    fig_cat = px.bar(
    top_categories,
    x='tickets',
    y='category',
    orientation='h',
    title='Top Issue Categories'
    )

    fig_cat.update_traces(marker_color=PRIMARY_COLOR)
    fig_cat.update_layout(
        xaxis_title='Tickets',
        yaxis_title='Category',
        height=320
    )
    fig_cat.update_traces(marker_color=PRIMARY_COLOR)
    fig_cat.update_layout(
        xaxis_title='Tickets',
        yaxis_title='Category',
        height=320
    )
    st.plotly_chart(fig_cat, use_container_width=True)

st.info(
    f"📌 A categoria com maior volume de issues é **{top_category}**, o que pode indicar um gargalo operacional prioritário."
    )

st.divider()

# -------------------------
# TEAM PERFORMANCE
# -------------------------
st.markdown("## 👥 Team Performance")

c4 , c5, c6 = st.columns([1,1,1.2])

with c4:
    tickets_by_analyst = tickets_by_analyst.sort_values("tickets", ascending=False)

    fig_analyst_volume = px.bar(
        tickets_by_analyst,
        x='analyst',
        y='tickets',
        title='Tickets per Analyst'
    )
    fig_analyst_volume.update_traces(marker_color=PRIMARY_COLOR)
    fig_analyst_volume.update_layout(
        showlegend=False,
        xaxis_title='Analyst',
        yaxis_title='Tickets',
        height=320
    )
    st.plotly_chart(fig_analyst_volume, use_container_width=True)

with c5:
    resolution_by_analyst = resolution_by_analyst.sort_values("avg_resolution", ascending=True)

    fig_resolution = px.bar(
        resolution_by_analyst,
        x='avg_resolution',
        y='alias',
        orientation='h',
        title='Average Resolution by Analyst',
        color='avg_resolution',
        color_continuous_scale='Blues'
    )
    fig_resolution.update_layout(
        xaxis_title='Avg Resolution Time(days)',
        yaxis_title='Analyst',
        height=320
    )
    st.plotly_chart(fig_resolution, use_container_width=True)

with c6:
    avg_tickets_team = performance_df["tickets"].mean() if not performance_df.empty else 0
    avg_resolution_team = performance_df["avg_resolution"].mean() if not performance_df.empty else 0

    fig_perf = px.scatter(
        performance_df,
        x='tickets',
        y='avg_resolution',
        text='alias',
        size='tickets',
        title='Perfomance Quadrant: Volume vs Resolution Time'
    )
    fig_perf.add_vline(x=avg_tickets_team, line_dash='dash', line_color='gray')
    fig_perf.add_hline(y=avg_resolution_team, line_dash='dash', line_color='gray')
    fig_perf.update_layout(
        xaxis_title='Tickets',
        yaxis_title='Avg Resolution Time(days)',
        height=320
    )
    st.plotly_chart(fig_perf, use_container_width=True)

st.success(f"🏆 Melhor performance em tempo médio: **{best_analyst}**.")
st.info(f"📦 Maior concentração de volume: **{top_volume_analyst}**.")

st.divider()

# -------------------------
# OPTIONAL DETAIL
# -------------------------
with st.expander("Ver distribuição detalhada do tempo de resolução"):
    fig_hist = px.histogram(
        filtered_df,
        x='resolution_time_days',
        nbins=30,
        title='Resolution Time Distribution'
    )
    fig_hist.update_traces(marker_color=PRIMARY_COLOR, marker=dict(line=dict(width=0)))
    fig_hist.update_layout(
        xaxis_title='Resolution Time(days)',
        yaxis_title='Frequency',
        bargap=0.08,
        height=320
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# -------------------------
# RECOMMENDED ACTIONS
# -------------------------
st.markdown("## ✅ Recommended Actions")

actions = []

if current_kpis["sla_compliance"] < 80:
    actions.append("Revisar gargalos no fluxo operacional para elevar o cumprimento de SLA.")

if current_kpis["open_tickets"] > current_kpis["total_tickets"] * 0.20:
    actions.append("Priorizar a redução do backlog aberto para evitar acumulo e envelhecimento de ticekts.")

if top_category != "N/A":
    actions.append(f"Investigar a categoria **{top_category}**, que representa o maior volume de issues no periodo.")

if not performance_df.empty:
    slowest_analyst = performance_df.sort_values("avg_resolution", ascending=False).iloc[0]['alias']
    actions.append(f"Avaliar coaching, redistribuição de carga ou revisão de processo para **{slowest_analyst}**, que teve o maior tempo medio de resolução.")

if previous_kpis is not None and not previous_df.empty:
    if current_kpis["resolution_rate"] < previous_kpis["resolution_rate"]:
        actions.append("A taxa de resolução caiu versus o período anterior; revisar capacidade, fila e priorização.")
    if current_kpis["sla_compliance"] < previous_kpis["sla_compliance"]:
        actions.append("O cumprimento de SLA caiu versus o período anterior; investigar mudanças de volume, categoria ou distribuição da carga.")
    if current_kpis["avg_resolution"] > previous_kpis["avg_resolution"]:
        actions.append("O tempo médio de resolução aumentou; revisar gargalos e tickets de maior complexidade.")

actions.append("Monitorar a distribuição de tickets entre analistas para reduzir concentração excessiva de volume.")
actions.append("Usar este dashboard em acompanhamento semanal para identificar desvios rapidamente.")

for action in actions:
    st.markdown(f" - {action}")
