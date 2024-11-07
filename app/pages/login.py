"""
Updated login page with case-insensitive email handling.
File: app/pages/login.py
"""

import streamlit as st
from app.auth.auth_handler import AuthHandler

def render_login_page():
    """Render the login/register page"""
    auth_handler = AuthHandler()
    
    st.title("Welcome to Stock Analysis")
    
    # Initialize tab selection in session state if not present
    if 'auth_tab' not in st.session_state:
        st.session_state.auth_tab = 0  # 0 for login, 1 for register
    
    # Create tabs
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    # Login tab
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email").lower().strip()  # Convert to lowercase and trim whitespace
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    token = auth_handler.login_user(email, password)
                    if token:
                        st.session_state.auth_token = token
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
    
    # Registration tab
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email").lower().strip()  # Convert to lowercase and trim whitespace
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_button = st.form_submit_button("Register")
            
            if submit_button:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields")
                elif not '@' in new_email:
                    st.error("Please enter a valid email address")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                else:
                    if auth_handler.register_user(new_email, new_password):
                        # Automatically log in the user
                        token = auth_handler.login_user(new_email, new_password)
                        if token:
                            st.session_state.auth_token = token
                            st.success("Registration successful! Logging you in...")
                            st.rerun()
                        else:
                            st.error("Registration successful but auto-login failed. Please log in manually.")
                    else:
                        st.error("Email already exists")

    # Switch to the appropriate tab based on session state
    if st.session_state.auth_tab == 0:
        tab1.__enter__()
    else:
        tab2.__enter__()