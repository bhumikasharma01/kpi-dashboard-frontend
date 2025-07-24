import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import os

def render_view_report(uploaded_file_path):
    st.title("📊 Monthly Report Summary")

    # Read Excel file
    df = pd.read_excel(uploaded_file_path)

    st.subheader("📈 Report Data Preview")
    st.dataframe(df)

    # Bar Plot Example
    st.subheader("📊 Cluster-wise Summary")
    cluster_col = st.selectbox("Select cluster column", df.columns)
    value_col = st.selectbox("Select value column", df.columns)

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(data=df, x=cluster_col, y=value_col, ax=ax)
    st.pyplot(fig)

    # PDF Generation
    if st.button("📥 Download as PDF"):
        pdf_path = create_pdf(df, cluster_col, value_col)
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="report.pdf")


def create_pdf(df, cluster_col, value_col):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Monthly Report", ln=True, align="C")

    pdf.ln(10)
    for index, row in df.iterrows():
        line = f"{cluster_col}: {row[cluster_col]}, {value_col}: {row[value_col]}"
        pdf.cell(200, 10, txt=line, ln=True)

    output_path = "temp_report.pdf"
    pdf.output(output_path)
    return output_path
