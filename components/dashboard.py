import streamlit as st
import pandas as pd
import plotly.express as px
from api import get_kpi_data


def show_dashboard():
    st.title("📊 KPI Performance Dashboard")
    data = get_kpi_data()

    if not data:
        st.warning("No KPI data found.")
        return

    st.subheader("Top Performers - Current Month")
    for kpi, performers in data['top_performers'].items():
        st.write(f"**{kpi}:** {', '.join(performers)}")

    st.subheader("Cluster-wise Performance")
    cluster_df = pd.DataFrame(data['cluster_wise'])
    st.plotly_chart(px.bar(cluster_df, x='cluster', y='value', color='kpi', barmode='group'))

    st.subheader("Last 3 Months Stats")
    month_df = pd.DataFrame(data['last_3_months'])
    st.line_chart(month_df.set_index('month'))
