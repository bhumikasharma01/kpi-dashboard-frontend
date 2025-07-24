import streamlit as st
import requests
from config import API_BASE_URL

def login_ui():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if not username or not password:
            st.warning("Please enter both username and password.")
            return

        # 🔍 Debug prints
        print("Username entered:", username)
        print("Password entered:", password)

        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"username": username, "password": password}
            )

            # 🔍 Debug prints for response
            print("Response status code:", response.status_code)
            print("Response content:", response.text)

            if response.status_code == 200:
                token = response.json()['access_token']
                st.session_state['token'] = token
                st.success("Login successful")
                st.experimental_rerun()
            elif response.status_code == 422:
                st.error("Invalid input. Please enter both username and password.")
            else:
                st.error("Login failed. Please check your credentials.")
        except requests.exceptions.RequestException as e:
            st.error(f"Request failed: {e}")

def is_logged_in():
    return 'token' in st.session_state

def logout_button():
    if st.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

