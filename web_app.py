import streamlit as st
from PIL import Image
from storage import load_json, save_json

st.set_page_config(page_title="Meraki", page_icon="🫐", layout="centered")

st.image("assets/homepage.png", use_container_width=True)
st.title("Meraki")

tab1, tab2, tab3 = st.tabs(["📝 Assignments", "📁 Projects", "⏱️ Study Timer"])

with tab1:
    st.subheader("Assignment Tracker")
    # Connect your assignment_tracker.py functions here

with tab2:
    st.subheader("Project Manager")
    # Connect your project_manager.py functions here

with tab3:
    st.subheader("Study Timer")
    # Connect your study_timer.py functions here
