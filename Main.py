import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
from streamlit_option_menu import option_menu

import Home,login, register

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rv171020",
    database="sales_management_system"
)

mycursor = mydb.cursor()

class MultiApp:
    def __init__(self):
        self.apps = []

    def add_app(self, title, func):
        self.apps.append({
            "title": title,
            "function": func
        })
    def run(self):
        with st.sidebar:
            app=option_menu(
                menu_title="Main Menu",
                options=["Home","Login","Register"],
                icons=["house", "person","person-plus"],
                menu_icon="cast",
                default_index=0
            )

        if app == "Home":
         Home.app()
        if app == "Login":
         login.app()
        if app == "Register":
         register.app()
        

app = MultiApp()
app.run()