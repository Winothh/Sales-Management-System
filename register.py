import streamlit as st
import mysql.connector
from mysql.connector import Error
import authlib as auth

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rv171020",
    database="sales_management_system"
)

mycursor = mydb.cursor()


def app():
    st.set_page_config(page_title="VR-SHOPPING", page_icon=":shopping_cart:", layout="wide")
    st.set_page_config(page_title="VR-SHOPPING", page_icon="🛒", layout="centered")

    st.markdown("""
        <style>
        .login-title { font-size: 2.5rem; font-weight: 800; color: #1a1a2e; }
        .login-sub   { color: #555; margin-bottom: 1.5rem; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-title">🛒 VR-SHOPPING</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Sales Management System — Please log in</div>', unsafe_allow_html=True)
    st.title("🔐 Register Page")
    st.write("Create a new account to access the VR-SHOPPING dashboard.")
    username = st.text_input("Username", key="register_username")
    password = st.text_input("Password", type="password", key="register_password")
    branch_id = st.text_input("Branch ID")
    role = st.text_input("Role", key="register_role")
    email = st.text_input("Email", key="register_email")

    if st.button("Register"):
            mycursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = mycursor.fetchone()
            if user:
                st.error("Username already exists.")
            else:
                mycursor.execute(
                "INSERT INTO users (username, password, branch_id, role, email) VALUES (%s, %s, %s, %s, %s)",
                (username, password, branch_id, role, email)
            )
            new_id = mycursor.lastrowid 
            mydb.commit()
            st.success("Registration successful! You can now log in.")


                