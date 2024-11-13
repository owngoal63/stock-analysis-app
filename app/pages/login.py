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
    
    # Create tabs
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    # Login tab
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email").lower().strip()
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Login")
            if submitted:
                if email and password:
                    token = auth_handler.login_user(email, password)
                    if token:
                        st.session_state.auth_token = token
                        st.session_state.current_page = "Home"
                        st.rerun()  # Force a rerun after successful login
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please fill in all fields")
    
    # Registration tab
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email").lower().strip()
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Register"):
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
                            st.session_state.current_page = "Home"
                            st.rerun()  # Force a rerun after successful registration and login
                        else:
                            st.error("Registration successful but auto-login failed. Please log in manually.")
                    else:
                        st.error("Email already exists")