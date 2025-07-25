import streamlit as st
import requests
import jwt  # PyJWT for decoding token
import io
import pandas as pd
import calendar
import datetime
import plotly.graph_objects as go
import os
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF
import base64
from matplotlib.patches import FancyBboxPatch
import sqlite3
import datetime
import fitz
import re





API_URL = "https://kpi-dashboard-backend-g61v.onrender.com"
JWT_SECRET = "your_secret_key"  # must match the backend secret used in create_access_token
ALGORITHM = "HS256"

def login(username, password):
    response = requests.post(
        f"{API_URL}/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        return None



def display_dashboard(data, month):

    
    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        
        df = pd.DataFrame([data])
        
    else:
        df = data.copy()
    df.columns = df.columns.str.strip()  # Clean spaces if any


    # Sort by Rank
    df = df.sort_values("Rank")

    # Section Heading
    st.markdown(f"## 🏆 Top 3 Clusters - {month}", unsafe_allow_html=True)

    # ---- PODIUM ----
    top3 = df.head(3)

    podium_positions = {
        1: {"x": 1, "y": 3.5, "color": "#FFD700"},
        2: {"x": 0, "y": 2.5, "color": "#C0C0C0"},
        3: {"x": 2, "y": 1.5, "color": "#CD7F32"},
    }

    fig = go.Figure()

    for _, row in top3.iterrows():
        rank = int(row["Rank"])
        cluster = row["Cluster"]
        pos = podium_positions[rank]

        fig.add_trace(go.Bar(
            x=[pos["x"]],
            y=[pos["y"]],
            name=f"{rank}: {cluster}",
            text=f"{cluster}",
            textposition="auto",
            marker_color=pos["color"],
            width=[0.5],
            hoverinfo='none'
        ))

        fig.add_annotation(
            x=pos["x"], y=pos["y"] + 0.4,
            text=f"<b>{rank}</b>",
            showarrow=False,
            font=dict(size=24),
        )

    fig.update_layout(
        height=400,
        width=600,
        #title="🏅 Top 3 Clusters",
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        plot_bgcolor="white",
    )

    st.plotly_chart(fig)

    # ---- COLORED RANKING TABLE ----
    def get_color(rank):
        if rank == 1:
            return 'background-color: #117A65'
        elif rank == 2:
            return 'background-color: #239B56 '
        elif rank == 3:
            return 'background-color: #1ABC9C'
        elif rank <= 5:
            return 'background-color: #F7DC6F'
        elif rank <= 7:
            return 'background-color: #EB984E'
        else:
            return 'background-color: #EC7063'
    



    styled_df = df.style.apply(
    lambda row: [get_color(row["Rank"])] * len(row), axis=1
)

    styled_df = styled_df.hide(axis="index")  # ✅ Hide row numbers

    st.markdown("### 📊 Full Cluster Rankings")
    st.dataframe(styled_df, use_container_width=True)

def admin_dashboard():
    if "role" not in st.session_state or st.session_state.role != "admin":
        st.error("❌ You must be an admin to access this page.")
        st.stop()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # st.title(f"📂 Select Dashboard Section")

    # Navigation bar
    option = st.radio("📂 Select Dashboard Section", ["User Dashboard", "Manage Users & Files"], horizontal=True)

    if option == "User Dashboard":
        # ==== USER DASHBOARD SECTION ====
        try:
            data = fetch_dashboard_data(token=st.session_state.token)
            if data:
                display_dashboard(data["rankings"], data["month"])
            else:
                st.warning("⚠️ No dashboard data available yet.")
        except Exception as e:
            st.error(f"❌ Exception during report fetching: {e}")

        st.subheader("📊 View Monthly Reports")

        def plot_podium_chart(podium_df):
            colors = ['#FFD700', '#C0C0C0', '#CD7F32']
            labels = podium_df["Cluster"].tolist()
            values = podium_df["Total Count Overall"].tolist()

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.set_xlim(0, 4)
            ax.set_ylim(0, max(values) * 1.3)
            ax.axis('off')

            positions = [2, 1, 3]
            for i, pos in enumerate(positions):
                height = values[i]
                label = labels[i]
                color = colors[i]

                bbox = FancyBboxPatch((pos - 0.25, 0), 0.5, height,
                                      boxstyle="round,pad=0.02", ec="none", fc=color, alpha=0.9)
                ax.add_patch(bbox)
                ax.text(pos, height + 20, f"{i + 1}", ha='center', va='bottom', fontsize=22, color='gray', fontweight='bold')
                ax.text(pos, height / 2, label, ha='center', va='center', fontsize=13, color='black', fontweight='bold')
                ax.text(pos, -30, f"Score: {height}", ha='center', va='top', fontsize=11, color='dimgray')

            ax.set_title(" Top 3 Clusters", fontsize=16, fontweight='bold', pad=30)
            return fig

        with st.form(key="monthly_report_form"):
            col1, col2 = st.columns(2)
            with col1:
                selected_month = st.selectbox("Select Month", list(calendar.month_name)[1:])
            with col2:
                selected_year = st.selectbox("Select Year", list(range(2025, 2031)))
            submit_button = st.form_submit_button("View Report")

        if submit_button:
            try:
                # url = f"https://kpi-dashboard-backend.onrender.com/upload/view?month={selected_month}&year={selected_year}"
                url = f"https://kpi-dashboard-backend.onrender.com/view_report_by_month?month={selected_month}&year={selected_year}"

                response = requests.get(url, headers=headers)
                st.write("Status code:", response.status_code)
                st.write("Raw response:", response.text) 

                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Report for {selected_month} {selected_year} loaded.")

                    podium_df = pd.DataFrame(data["podium"])
                    full_df = pd.DataFrame(data["rankings"])

                    st.write("### 🏆 Top 3 Clusters")
                    st.dataframe(podium_df)

                    st.write("### 📈 Ranking Chart")
                    fig = plot_podium_chart(podium_df)
                    st.pyplot(fig)

                    st.write("### 📋 Full Ranking Table")
                    st.dataframe(full_df)

                    # PDF download
                    class PDF(FPDF):
                        def header(self):
                            self.set_font('Arial', 'B', 14)
                            self.cell(0, 10, 'Monthly KPI Report', ln=True, align='C')
                            self.ln(5)

                        def footer(self):
                            self.set_y(-15)
                            self.set_font('Arial', 'I', 8)
                            self.cell(0, 10, f'Page {self.page_no()}', align='C')

                    def generate_pdf(podium_df, full_df, chart_fig, selected_month, selected_year):
                        pdf = PDF()
                        pdf.add_page()
                        pdf.set_font("Arial", size=12)
                        pdf.cell(200, 10, txt=f"{selected_month} {selected_year}", ln=True, align='C')
                        pdf.ln(10)

                        chart_bytes = BytesIO()
                        chart_fig.savefig(chart_bytes, format='PNG', bbox_inches="tight")
                        chart_bytes.seek(0)
                        with open("temp_chart.png", "wb") as f:
                            f.write(chart_bytes.read())
                        pdf.image("temp_chart.png", x=15, w=180)
                        os.remove("temp_chart.png")
                        pdf.ln(10)

                        pdf.set_font("Arial", size=11, style='B')
                        pdf.cell(200, 10, txt="Full Rankings Table:", ln=True)
                        pdf.ln(5)

                        col_widths = [20, 100, 60]
                        headers = ["Rank", "Cluster", "Total Count"]

                        pdf.set_fill_color(230, 230, 230)
                        pdf.set_font("Arial", "B", 11)
                        for i, header in enumerate(headers):
                            pdf.cell(col_widths[i], 10, header, border=1, align='C', fill=True)
                        pdf.ln()

                        pdf.set_font("Arial", "", 11)
                        for i, (_, row) in enumerate(full_df.iterrows()):
                            fill = i < 3
                            pdf.set_fill_color(200, 255, 200 if fill else 255)
                            pdf.cell(col_widths[0], 10, str(row["Rank"]), border=1, align='C', fill=fill)
                            pdf.cell(col_widths[1], 10, str(row["Cluster"]), border=1, fill=fill)
                            pdf.cell(col_widths[2], 10, str(row["Total Count Overall"]), border=1, align='C', fill=fill)
                            pdf.ln()

                        return pdf.output(dest='S').encode('latin1')

                    try:
                        pdf_bytes = generate_pdf(podium_df, full_df, fig, selected_month, selected_year)
                        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="KPI_Report_{selected_month}_{selected_year}.pdf">📄 Download PDF Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"⚠️ Something went wrong: {str(e)}")
                else:
                    st.error(f"❌ Error: {response.json().get('detail')}")
            except Exception as e:
                st.error(f"⚠️ Something went wrong: {str(e)}")

        st.subheader("📊 Cluster Rank Over Past 3 Months")
        clusters = ["MNG", "MPCG", "PUH", "TUP", "KOB", "MUM", "KTN", "KAP", "RAD", "GUJ"]
        selected_cluster = st.selectbox("Select Cluster", clusters)

        today = datetime.datetime.today()
        past_months = [(today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)]
        for _ in range(2):
            prev = past_months[-1].replace(day=1) - datetime.timedelta(days=1)
            past_months.append(prev.replace(day=1))
        past_months.reverse()

        API_URL = "https://kpi-dashboard-backend.onrender.com"
        response = requests.get(f"{API_URL}/upload/all_generated")

        if response.status_code == 200:
            reports = response.json()
            results = []
            for date in past_months:
                month_name = calendar.month_name[date.month]
                year = date.year
                expected_filename = f"Full_Rankings_{month_name}_{year}.pdf"
                matched = next((r for r in reports if r["pdf_filename"] == expected_filename), None)

                if matched:
                    pdf_bytes = base64.b64decode(matched["pdf_content"])
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    cluster_rank = None
                    for page in doc:
                        text = page.get_text()
                        for line in text.splitlines():
                            if selected_cluster.lower() in line.lower():
                                parts = line.split()
                                if len(parts) >= 3 and parts[-1].isdigit():
                                    cluster_rank = parts[-1]
                                    break
                        if cluster_rank:
                            break
                    results.append({"Month": f"{month_name} {year}", "Rank": cluster_rank or "Not Found"})
                else:
                    results.append({"Month": f"{month_name} {year}", "Rank": "Report Missing"})
            st.dataframe(pd.DataFrame(results))
        else:
            st.error("Failed to load generated reports.")

        show_cluster_score_summary()
    # ==== ADMIN SECTIONS ====
    elif option == "Manage Users & Files":
        # Paste full block from: 
        # --> 👥 User Management
        # --> 📁 Manage Excel Files
        # --> 🧾 Generate Monthly Report PDF
        # (Already implemented in your current admin_dashboard function)
        # Just keep them here unchanged
        st.markdown("## 👥 User Management")
        if "show_add_user_form" not in st.session_state:
            st.session_state.show_add_user_form = False

        if "show_delete_user_form" not in st.session_state:
            st.session_state.show_delete_user_form = False

        # --- Control buttons ---
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("➕ Add New User"):
                st.session_state.show_add_user_form = True
                st.session_state.show_delete_user_form = False  # Hide other form

        with col2:
            if st.button("🗑️ Delete User"):
                st.session_state.show_delete_user_form = True
                st.session_state.show_add_user_form = False  # Hide other form
        with col3:
            if st.button("👁️ View All Users"):
                try:
                    users_resp = requests.get("{API_URL}/auth/users", headers=headers)
                    if users_resp.status_code == 200:
                        users = users_resp.json()

                        if users:
                            user_table = [{"Username": user["username"], "Role": user["role"]} for user in users]
                            st.table(user_table)
                        else:
                            st.info("No users found.")
                    else:
                        st.error(f"Failed to fetch users. Status: {users_resp.status_code}")
                except Exception as e:
                    st.error(f"❌ Exception while loading users: {e}")
        # -----------------------------
        # 🧾 Add User Form
        # -----------------------------
        if st.session_state.show_add_user_form:
            st.markdown("### ➕ Add New User")
            with st.form("create_user_form"):
                new_username = st.text_input("Username", help="Should be your name, start with a capital letter, and max 20 characters.")
                new_password = st.text_input(
                    "Password", 
                    type="password", 
                    help="Password must be 4-10 characters, with at least 1 uppercase and 1 lowercase letter."
                )
                new_role = st.selectbox("Role", ["admin", "user"])
                submit_btn = st.form_submit_button("✅ Create User")

                def validate_username(username):
                    return (
                        username.istitle() and   # Starts with capital, rest lowercase
                        len(username) <= 20 and
                        username.isalpha()       # Only alphabets (optional, can allow numbers if needed)
                    )

                def validate_password(password):
                    return (
                        4 <= len(password) <= 10 and
                        re.search(r"[A-Z]", password) and
                        re.search(r"[a-z]", password)
                    )

                if submit_btn:
                    if not new_username or not new_password:
                        st.warning("⚠️ Please fill in both username and password.")
                    elif not validate_username(new_username):
                        st.error("❌ Username must start with a capital letter, be your name, and not exceed 20 characters.")
                    elif not validate_password(new_password):
                        st.error("❌ Password must be 4-10 characters long and include at least one uppercase and one lowercase letter.")
                    else:
                        try:
                            payload = {
                                "username": new_username,
                                "password": new_password,
                                "role": new_role
                            }
                            response = requests.post("{API_URL}/auth/create-user", json=payload, headers=headers)
                            if response.status_code == 200:
                                st.success("🎉 User created successfully.")
                                st.session_state.show_add_user_form = False
                            else:
                                st.error(f"❌ Error: {response.json().get('detail')}")
                        except Exception as e:
                            st.error(f"❌ Exception: {e}")

        # -----------------------------
        # ❌ Delete User Form
        # -----------------------------
        if st.session_state.show_delete_user_form:
            st.markdown("### 🗑️ Delete User")
            try:
                users_resp = requests.get("{API_URL}/auth/users", headers=headers)
                if users_resp.status_code == 200:
                    users = users_resp.json()
                    usernames = [u["username"] for u in users if u["username"] != st.session_state.username]
                    if usernames:
                        selected_user = st.selectbox("Select user to delete", usernames)
                        confirm = st.checkbox("✅ I confirm I want to delete this user")
                        if st.button("🗑️ Confirm Delete") and confirm:
                            try:
                                del_resp = requests.delete(
                                    f"{API_URL}/auth/delete-user",
                                    params={"username": selected_user},
                                    headers=headers
                                )
                                if del_resp.status_code == 200:
                                    st.success(f"✅ User '{selected_user}' deleted.")
                                    st.session_state.show_delete_user_form = False
                                else:
                                    st.error(f"❌ Error: {del_resp.json().get('detail')}")
                            except Exception as e:
                                st.error(f"❌ Exception: {e}")
                    else:
                        st.info("No other users available to delete.")
                else:
                    st.error("Failed to load users.")
            except Exception as e:
                st.error(f"❌ Error fetching users: {e}")
        # paste user management block
        # if st.button("👁️ View All Users"):
        #     try:
        #         users_resp = requests.get("{API_URL}/auth/users", headers=headers)
        #         if users_resp.status_code == 200:
        #             users = users_resp.json()

        #             if users:
        #                 # Only keep necessary fields: username and role
        #                 user_table = [{"Username": user["username"], "Role": user["role"]} for user in users]

        #                 # Display in table
        #                 st.table(user_table)
        #             else:
        #                 st.info("No users found.")
        #         else:
        #             st.error(f"Failed to fetch users. Status: {users_resp.status_code}")
        #     except Exception as e:
        #         st.error(f"❌ Exception while loading users: {e}")
        st.markdown("---")
        st.markdown("## 📁 Manage Excel Files")
        tab1, tab2, tab3 = st.tabs(["⬆️ Upload", "⬇️ Download", "🗑️ Delete"])

    # ---------------------
    # TAB 1: UPLOAD SECTION
    # ---------------------
        with tab1:
            st.markdown("### ⬆️ Upload Excel Files")
            st.markdown("Upload monthly KPI Excel reports.")

            with st.form("upload_form"):
                col1, col2 = st.columns(2)
                with col1:
                    month = st.selectbox("Select Month", list(calendar.month_name)[1:])
                with col2:
                    year = st.number_input("Enter Year", min_value=2020, max_value=datetime.datetime.now().year, value=datetime.datetime.now().year)

                uploaded_file = st.file_uploader("📁 Upload Excel File", type=["xlsx"])
                submitted = st.form_submit_button("Upload Report")

                if submitted and uploaded_file:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    params = {"month": month, "year": year}

                    check_resp = requests.get("{API_URL}/upload/reports", headers=headers, params=params)
                    existing = check_resp.json() if check_resp.status_code == 200 else None

                    replace = False
                    if existing:
                        st.warning(f"Report for {month} {year} already exists.")
                        replace = st.checkbox("✅ Replace existing report")

                    data = {"month": month, "year": year, "replace": str(replace)}
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

                    upload_resp = requests.post("{API_URL}/upload/reports", data=data, files=files, headers=headers)

                    if upload_resp.status_code == 200:
                        st.success("✅ Report uploaded successfully!")
                    else:
                        st.error("❌ Upload failed. " + upload_resp.text)

        # -----------------------
        # TAB 2: DOWNLOAD SECTION
        # -----------------------
        with tab2:
            st.markdown("### ⬇️ Download Excel Reports")

            with st.form(key="report_filter_form"):
                col1, col2, col3 = st.columns([4, 4, 2])
                with col1:
                    filter_month = st.selectbox("Filter by Month", [""] + list(calendar.month_name)[1:], key="month_filter")
                with col2:
                    filter_year = st.number_input("Filter by Year", 2020, datetime.datetime.now().year, datetime.datetime.now().year, key="year_filter")
                with col3:
                    st.markdown("### ")
                    submitted = st.form_submit_button("🔍 Search")

            if submitted:
                params = {}
                if filter_month:
                    params["month"] = filter_month
                if filter_year:
                    params["year"] = filter_year

                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    response = requests.get("{API_URL}/upload/reports", headers=headers, params=params)
                    reports = response.json() if response.status_code == 200 else []

                    if reports:
                        for rep in reports:
                            with st.expander(f"{rep['filename']}"):
                                st.write(f"📅 **Month-Year:** {rep['month']} {rep['year']}")
                                st.write(f"👤 **Uploaded by:** {rep['uploaded_by']}")
                                download_url = f"{API_URL}/upload/reports/download?month={rep['month']}&year={rep['year']}"
                                download_resp = requests.get(download_url, headers=headers)

                                if download_resp.status_code == 200:
                                    st.download_button(
                                        label="⬇️ Download Report",
                                        data=download_resp.content,
                                        file_name=rep["filename"],
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"download_{rep['month']}_{rep['year']}"
                                    )
                                else:
                                    st.error("❌ Failed to fetch report.")
                    else:
                        st.info("No reports found for selected filters.")
                except Exception as e:
                    st.error(f"❌ Error loading reports: {e}")

        # ---------------------
        # TAB 3: DELETE SECTION
        # ---------------------
        with tab3:
            st.markdown("### 🗑️ Delete Excel Reports")

            with st.form(key="delete_report_filter_form"):
                col1, col2, col3 = st.columns([4, 4, 2])
                with col1:
                    del_month = st.selectbox("Filter by Month", [""] + list(calendar.month_name)[1:], key="delete_month_filter")
                with col2:
                    del_year = st.number_input("Filter by Year", 2020, datetime.datetime.now().year, datetime.datetime.now().year, key="delete_year_filter")
                with col3:
                    st.markdown("### ")
                    delete_submitted = st.form_submit_button("🔍 Search")

            if "delete_reports_cache" not in st.session_state:
                st.session_state.delete_reports_cache = []

            if delete_submitted:
                params = {}
                if del_month:
                    params["month"] = del_month
                if del_year:
                    params["year"] = del_year

                try:
                    response = requests.get("{API_URL}/upload/reports", headers=headers, params=params)
                    st.session_state.delete_reports_cache = response.json() if response.status_code == 200 else []
                except Exception as e:
                    st.error(f"❌ Error fetching reports: {e}")

            if st.session_state.delete_reports_cache:
                for idx, rep in enumerate(st.session_state.delete_reports_cache):
                    with st.expander(f"{rep['filename']}"):
                        st.write(f"📅 **Month-Year:** {rep['month']} {rep['year']}")
                        with st.form(key=f"delete_form_{idx}"):
                            delete_btn = st.form_submit_button("🗑️ Delete Report")
                            if delete_btn:
                                try:
                                    del_resp = requests.delete(
                                        "{API_URL}/upload/reports/delete",
                                        headers=headers,
                                        params={"month": rep["month"], "year": rep["year"]}
                                    )
                                    if del_resp.status_code == 200:
                                        st.success(f"✅ Report '{rep['filename']}' deleted successfully.")
                                        st.session_state.delete_reports_cache.remove(rep)
                                    else:
                                        st.error("❌ Deletion failed.")
                                except Exception as e:
                                    st.error(f"❌ Error deleting report: {e}")
            elif delete_submitted:
                st.info("No reports found for selected filters.")
        # paste Excel file tab logic (Upload, Download, Delete)

        st.subheader("🧾 Generate Monthly Report PDF")
        # paste monthly report generation logic
        month_options = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
        selected_month = st.selectbox("Select Month", month_options)
        selected_year = st.selectbox("Select Year", list(range(2025, datetime.datetime.now().year + 1)))

        # 📤 Generate PDF button
        if st.button("Generate PDF Report"):
            with st.spinner("Generating PDF..."):
                try:
                    API_URL = "{API_URL}/upload/generate_pdf"

                    # If you're using access_token anyway, you can keep this, or remove it completely.
                    # headers = {}
                    # if "access_token" in st.session_state:
                    #     headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}

                    response = requests.post(
                        API_URL,
                        headers=headers,
                        params={"month": selected_month, "year": selected_year}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ PDF generated successfully: {data['filename']}")
                    else:
                        st.error(f"❌ Failed to generate PDF: {response.json().get('detail', 'Unknown error')}")

                except Exception as e:
                    st.error(f"⚠️ Error: {str(e)}")


#       
def user_dashboard():
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None

    try:
        data = fetch_dashboard_data(token=st.session_state.token)
        if data:
           display_dashboard(data["rankings"], data["month"])

        else:
            st.warning("⚠️ No dashboard data available yet.")
    except Exception as e:
        st.error(f"❌ Exception during report fetching: {e}")

    st.subheader("📊 View Monthly Reports")
    

    def plot_podium_chart(podium_df):
        colors = ['#FFD700', '#C0C0C0', '#CD7F32']  # gold, silver, bronze
        labels = podium_df["Cluster"].tolist()
        values = podium_df["Total Count Overall"].tolist()
        
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_xlim(0, 4)
        ax.set_ylim(0, max(values) * 1.3)
        ax.axis('off')

        positions = [2, 1, 3]  # Center gold, then silver left, bronze right

        for i, pos in enumerate(positions):
            height = values[i]
            label = labels[i]
            color = colors[i]

            # Draw rounded rectangle bar
            bbox = FancyBboxPatch(
                (pos - 0.25, 0), 0.5, height,
                boxstyle="round,pad=0.02",
                ec="none", fc=color, alpha=0.9
            )
            ax.add_patch(bbox)

            # Rank number above bar
            ax.text(pos, height + 20, f"{i + 1}",
                    ha='center', va='bottom', fontsize=22, color='gray', fontweight='bold')

            # Cluster name inside the bar
            ax.text(pos, height / 2, label,
                    ha='center', va='center', fontsize=13, color='black', fontweight='bold')

            # Score below the bar
            ax.text(pos, -30, f"Score: {height}",
                    ha='center', va='top', fontsize=11, color='dimgray')

        ax.set_title(" Top 3 Clusters", fontsize=16, fontweight='bold', pad=30)

        return fig

    with st.form(key="monthly_report_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_month = st.selectbox("Select Month", [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ])
        with col2:
            selected_year = st.selectbox("Select Year", list(range(2025, 2031)))

        submit_button = st.form_submit_button("View Report")

    if submit_button:
        try:
            headers = {"Authorization": f"Bearer {st.session_state['token']}"}
            url = f"{API_URL}/upload/view?month={selected_month}&year={selected_year}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ Report for {selected_month} {selected_year} loaded.")

                podium_df = pd.DataFrame(data["podium"])
                full_df = pd.DataFrame(data["rankings"])

                st.write("### 🏆 Top 3 Clusters")
                st.dataframe(podium_df)

                st.write("### 📈 Ranking Chart")
                fig = plot_podium_chart(podium_df)
                st.pyplot(fig)

                st.write("### 📋 Full Ranking Table")
                st.dataframe(full_df)

                # PDF Download Section
                st.write("### 📥 Download Report as PDF")
                class PDF(FPDF):
                    def header(self):
                        self.set_font('Arial', 'B', 14)
                        self.cell(0, 10, 'Monthly KPI Report', ln=True, align='C')
                        self.ln(5)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font('Arial', 'I', 8)
                        self.cell(0, 10, f'Page {self.page_no()}', align='C')

                def generate_pdf(podium_df, full_df, chart_fig, selected_month, selected_year):
                    pdf = PDF()
                    pdf.add_page()
                    pdf.set_font("Arial", size=12)

                    # Title
                    pdf.set_font("Arial", size=12, style='B')
                    pdf.cell(200, 10, txt=f"{selected_month} {selected_year}", ln=True, align='C')
                    pdf.ln(10)

                   

                    # Save chart to PNG and add to PDF
                    chart_bytes = BytesIO()
                    chart_fig.savefig(chart_bytes, format='PNG', bbox_inches="tight")
                    chart_bytes.seek(0)

                    with open("temp_chart.png", "wb") as f:
                        f.write(chart_bytes.read())
                    pdf.image("temp_chart.png", x=15, w=180)
                    os.remove("temp_chart.png")

                    pdf.ln(10)

                    # Full Rankings Table
                    pdf.set_font("Arial", size=11, style='B')
                    pdf.cell(200, 10, txt="Full Rankings Table:", ln=True)
                    pdf.ln(5)

                    # Table headers
                    col_widths = [20, 100, 60]  # Adjust as needed
                    headers = ["Rank", "Cluster", "Total Count"]

                    pdf.set_fill_color(230, 230, 230)
                    pdf.set_font("Arial", "B", 11)
                    for i, header in enumerate(headers):
                        pdf.cell(col_widths[i], 10, header, border=1, align='C', fill=True)
                    pdf.ln()

                    # Table rows
                    # Table rows with top 3 highlight
                    pdf.set_font("Arial", "", 11)

                    for i, (_, row) in enumerate(full_df.iterrows()):
                        if i < 3:  # Top 3 rows
                            pdf.set_fill_color(200, 255, 200)
                            fill = True
                        else:
                            pdf.set_fill_color(255, 255, 255)  # White background
                            fill = False

                        pdf.cell(col_widths[0], 10, str(row["Rank"]), border=1, align='C', fill=fill)
                        pdf.cell(col_widths[1], 10, str(row["Cluster"]), border=1, fill=fill)
                        pdf.cell(col_widths[2], 10, str(row["Total Count Overall"]), border=1, align='C', fill=fill)
                        pdf.ln()


                    # Return PDF as bytes
                    pdf_bytes = pdf.output(dest='S').encode('latin1')
                    return pdf_bytes
                try:
                    pdf_bytes = generate_pdf(podium_df, full_df, fig, selected_month, selected_year)
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="KPI_Report_{selected_month}_{selected_year}.pdf">📄 Download PDF Report</a>'
                    st.markdown(href, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"⚠️ Something went wrong: {str(e)}")
                    
        #             output = BytesIO()
        #             pdf.output(output)
        #             return output.getvalue()

        #         pdf_bytes = generate_pdf(data, fig)
        #         b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        #         href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="KPI_Report_{selected_month}_{selected_year}.pdf">📄 Download PDF Report</a>'
        #         st.markdown(href, unsafe_allow_html=True)

            else:
                st.error(f"❌ Error: {response.json().get('detail')}")

        except Exception as e:
            st.error(f"⚠️ Something went wrong: {str(e)}")

   

    
            st.error(f"🚨 Error occurred while fetching report: {str(e)}")
    
    st.subheader("📊 Cluster Rank Over Past 3 Months")

# 🧾 Cluster dropdown
    clusters = ["MNG", "MPCG", "PUH", "TUP", "KOB", "MUM", "KTN", "KAP", "RAD", "GUJ"]
    selected_cluster = st.selectbox("Select Cluster", clusters)

    # ⏳ Calculate last 3 months (excluding current month)
   
    today = datetime.datetime.today()
    past_months = [(today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)]
    

    for _ in range(2):
        prev = past_months[-1].replace(day=1) - datetime.timedelta(days=1)
        past_months.append(prev.replace(day=1))

    past_months.reverse()  # So we show oldest to latest
    API_URL = "{API_URL}/upload/all_generated"
    response = requests.get(API_URL)  # Removed headers

    if response.status_code == 200:
        reports = response.json()
        results = []

        for date in past_months:
            month_name = calendar.month_name[date.month]
            year = date.year
            expected_filename = f"Full_Rankings_{month_name}_{year}.pdf"

            matched = next((r for r in reports if r["pdf_filename"] == expected_filename), None)
            if matched:
                # Read PDF content
                pdf_bytes = base64.b64decode(matched["pdf_content"])
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                cluster_rank = None

                for page in doc:
                    text = page.get_text()
                    lines = text.splitlines()
                    for line in lines:
                        if selected_cluster.lower() in line.lower():
                            parts = line.split()
                            if len(parts) >= 3 and parts[-1].isdigit():
                                cluster_rank = parts[-1]
                                break
                    if cluster_rank:
                        break

                results.append({
                    "Month": f"{month_name} {year}",
                    "Rank": cluster_rank if cluster_rank else "Not Found"
                })
            else:
                results.append({
                    "Month": f"{month_name} {year}",
                    "Rank": "Report Missing"
                })

        df_result = pd.DataFrame(results)
        st.dataframe(df_result)

    else:
        st.error("Failed to load generated reports.")
    show_cluster_score_summary()

def show_cluster_score_summary():
    st.subheader("📋 Cluster Rank & Score Over Last 3 Months")

    # 📅 Get last 3 months (excluding current)
    today = datetime.datetime.today()
    past_months = [(today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)]
    for _ in range(2):
        prev = past_months[-1].replace(day=1) - datetime.timedelta(days=1)
        past_months.append(prev.replace(day=1))
    past_months.reverse()

    # Just month names for labels (no year)
    month_labels = [calendar.month_name[dt.month] for dt in past_months]

    clusters = ["MNG", "MPCG", "PUH", "TUP", "KOB", "MUM", "KTN", "KAP", "RAD", "GUJ"]
    cluster_data = {cluster: {} for cluster in clusters}

    # 📦 Fetch reports
    API_URL = "{API_URL}/upload/all_generated"
    response = requests.get(API_URL)

    if response.status_code != 200:
        st.error("❌ Failed to load generated reports.")
        return

    reports = response.json()

    for date_obj, label in zip(past_months, month_labels):
        month_name = calendar.month_name[date_obj.month]
        year = date_obj.year
        expected_filename = f"Full_Rankings_{month_name}_{year}.pdf"

        matched = next((r for r in reports if r["pdf_filename"] == expected_filename), None)

        if not matched:
            for cluster in clusters:
                cluster_data[cluster][label] = ("Missing", "Missing")
            continue

        try:
            pdf_bytes = base64.b64decode(matched["pdf_content"])
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            for page in doc:
                text = page.get_text()
                lines = text.splitlines()

                for line in lines:
                    for cluster in clusters:
                        if cluster.lower() in line.lower():
                            parts = line.split()
                            if len(parts) >= 3:
                                try:
                                    rank = parts[-2]
                                    score = parts[-1]
                                    cluster_data[cluster][label] = (rank, score)
                                except:
                                    cluster_data[cluster][label] = ("Error", "Error")

            for cluster in clusters:
                if label not in cluster_data[cluster]:
                    cluster_data[cluster][label] = ("Not Found", "Not Found")

        except Exception as e:
            for cluster in clusters:
                cluster_data[cluster][label] = ("Error", "Error")

    # 🧾 Prepare DataFrame with short column names
    columns = ["Cluster"]
    for label in month_labels:
        columns.append(f"{label} Rank")
        columns.append(f"{label} Score")

    data_rows = []
    for cluster in clusters:
        row = [cluster]
        for label in month_labels:
            rank, score = cluster_data[cluster].get(label, ("-", "-"))
            row.extend([score, rank])  # Note: Order switched to match column labels
        data_rows.append(row)

    df_result = pd.DataFrame(data_rows, columns=columns)
    def style_scores(df):
        styled_df = pd.DataFrame("", index=df.index, columns=df.columns)

        for col in df.columns:
            if col == "Cluster":
                # Off-white for cluster name column
                styled_df[col] = "background-color: yellow; color: black;"
            elif "Rank" in col:
                # Light yellow for rank columns
                styled_df[col] = "background-color: lightpink; color: black;"
            elif "Score" in col:
                try:
                    scores = pd.to_numeric(df[col], errors="coerce")
                    max_score = scores.max()
                except:
                    continue

                for i in df.index:
                    cell_value = pd.to_numeric(df.loc[i, col], errors="coerce")
                    if pd.isna(cell_value):
                        continue
                    if cell_value == max_score:
                        styled_df.loc[i, col] = "background-color: lightgreen; color: black;"
                    else:
                        styled_df.loc[i, col] = "background-color: lightblue; color: black;"

        return styled_df


    styled_df = df_result.style.apply(style_scores, axis=None)
    styled_df = styled_df.hide(axis="index")

    st.dataframe(styled_df, use_container_width=True)
    # st.dataframe(df_result, use_container_width=True)



    
def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("role"), payload.get("sub")  # return role and username
    except jwt.ExpiredSignatureError:
        st.error("Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        st.error("Invalid token. Please log in again.")
    return None, None

def fetch_dashboard_data(token):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.get("{API_URL}/kpi/dashboard", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Exception during report fetching: {e}")
        return None





# --- Session Init ---
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

# --- Login Form ---
if not st.session_state.token:
    st.title("🔐 KPI Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            token = login(username, password)
            if token:
                role, username = decode_token(token)
                if role:
                    st.session_state.token = token
                    st.session_state.role = role
                    st.session_state.username = username
                    st.success(f"✅ Login successful! Welcome {username} ({role})")
                    st.rerun()

                else:
                    st.error("Failed to decode role from token.")
            else:
                st.error("❌ Invalid username or password.")

# --- Logout ---
else:
    st.sidebar.title("🔧 Menu")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()


    # --- Role-based Dashboards ---
    st.title(f" Welcome {st.session_state.username}!")

    if st.session_state.role == "admin":
        admin_dashboard()  # ← Calls the function for admin users
    else:
        user_dashboard()


    # Shared section
    data = fetch_dashboard_data(st.session_state.token)
    if "error" in data:
        st.error(data["error"])
    



def upload_excel_report(username):
    st.subheader("📤 Upload Monthly KPI Report")

    with st.form("upload_form"):
        col1, col2 = st.columns(2)
        with col1:
            month = st.selectbox("Select Month", list(calendar.month_name)[1:])
        with col2:
            year = st.number_input("Enter Year", min_value=2020, max_value=datetime.datetime.now().year, value=datetime.datetime.now().year)

        uploaded_file = st.file_uploader("📁 Upload Excel File", type=["xlsx"])
        submitted = st.form_submit_button("Upload Report")

        if submitted and uploaded_file:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            params = {"month": month, "year": year}
            check_resp = requests.get("{API_URL}/upload/reports", headers=headers, params=params)

            try:
                check_resp.raise_for_status()
                existing = check_resp.json()
            except requests.exceptions.HTTPError:
                existing = None
            except requests.exceptions.JSONDecodeError:
                existing = None

            replace = False
            if existing:
                st.warning(f"Report for {month} {year} already exists.")
                replace = st.checkbox("✅ Replace existing report")

            data = {
                "month": month,
                "year": year,
                "uploaded_by": username,
                "replace": str(replace)
            }
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            upload_resp = requests.post("{API_URL}/upload/reports", data=data, files=files, headers=headers)
            if upload_resp.status_code == 200 and "message" in upload_resp.json():
                st.success("✅ Report uploaded successfully!")
            else:
                st.error("❌ Upload failed.")



