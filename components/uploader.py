import streamlit as st
from api import upload_file


def show_uploader():
    st.subheader("📁 Upload Monthly KPI Report")
    file = st.file_uploader("Choose an Excel file", type="xlsx")
    if file and st.button("Upload"):
        response = upload_file(file)
        if response.status_code == 200:
            st.success("File uploaded and processed successfully!")
        else:
            st.error("Upload failed. Check file format and try again.")
