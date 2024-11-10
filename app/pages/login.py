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

    def handle_login(email: str, password: str):
        """Handle login form submission"""
        if not email or not password:
            st.session_state.login_error = "Please fill in all fields"
        else:
            token = auth_handler.login_user(email, password)
            if token:
                st.session_state.auth_token = token
                st.session_state.login_success = "Login successful!"
                st.session_state.nav_clicked = True
                st.rerun()
            else:
                st.session_state.login_error = "Invalid email or password"

    def handle_register(email: str, password: str, confirm_password: str):
        """Handle registration form submission"""
        if not email or not password or not confirm_password:
            st.session_state.register_error = "Please fill in all fields"
        elif not '@' in email:
            st.session_state.register_error = "Please enter a valid email address"
        elif password != confirm_password:
            st.session_state.register_error = "Passwords do not match"
        elif len(password) < 8:
            st.session_state.register_error = "Password must be at least 8 characters long"
        else:
            if auth_handler.register_user(email, password):
                # Automatically log in the user
                token = auth_handler.login_user(email, password)
                if token:
                    st.session_state.auth_token = token
                    st.session_state.register_success = "Registration successful! Logging you in..."
                    st.session_state.nav_clicked = True
                    st.rerun()
                else:
                    st.session_state.register_error = "Registration successful but auto-login failed. Please log in manually."
            else:
                st.session_state.register_error = "Email already exists"
    
    # Login tab
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email").lower().strip()
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button(
                "Login",
                on_click=handle_login,
                args=(email, password)
            )
            
            if 'login_error' in st.session_state:
                st.error(st.session_state.login_error)
                st.session_state.pop('login_error')
            
            if 'login_success' in st.session_state:
                st.success(st.session_state.login_success)
                st.session_state.pop('login_success')
    
    # Registration tab
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email").lower().strip()
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit_button = st.form_submit_button(
                "Register",
                on_click=handle_register,
                args=(new_email, new_password, confirm_password)
            )
            
            if 'register_error' in st.session_state:
                st.error(st.session_state.register_error)
                st.session_state.pop('register_error')
            
            if 'register_success' in st.session_state:
                st.success(st.session_state.register_success)
                st.session_state.pop('register_success')