import requests
from config import API_BASE_URL


def get_headers():
    from streamlit import session_state
    return {"Authorization": f"Bearer {session_state['token']}"}


def upload_file(file):
    files = {"file": file}
    response = requests.post(f"{API_BASE_URL}/upload", files=files, headers=get_headers())
    return response


def get_kpi_data():
    response = requests.get(f"{API_BASE_URL}/kpi/dashboard", headers=get_headers())
    return response.json() if response.ok else {}
