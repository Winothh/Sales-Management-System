import streamlit as st  
import mysql.connector

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rv171020",
    database="sales_management_system"
)

mycursor = mydb.cursor()
def app():
    st.set_page_config(page_title="VR-SHOPPING", page_icon=":shopping_cart:", layout="wide")
    st.title("Welcome to :red[VR-SHOPPING] :shopping_cart:")
    st.header("Experience the :blue[Future of Shopping] in your Online Store!")
    st.image("https://s3.ap-south-1.amazonaws.com/prod-easebuzz-static/static/base/assets_aug_2021/img/easebuzz/easebuzz-explainer/explainers-ecommerce/start-online-store/6.png")
