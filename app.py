import streamlit as st

from src.database import initialize_database
from src.ui_components import apply_theme_css, render_sidebar_brand

st.set_page_config(
    page_title="StockWise AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme_css()
render_sidebar_brand()
initialize_database()

pages = {
    "Workspace": [
        st.Page(
            "pages/0_Dashboard.py",
            title="Dashboard",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/2_Products_Inventory.py",
            title="Products & Inventory",
            icon=":material/inventory_2:",
        ),
        st.Page(
            "pages/1_Data_Import.py",
            title="Data Import",
            icon=":material/upload_file:",
        ),
        st.Page(
            "pages/5_Reorder_Recommendations.py",
            title="Reorder Recommendations",
            icon=":material/auto_awesome:",
        ),
    ],
    "Insights": [
        st.Page(
            "pages/3_Sales_Analytics.py",
            title="Sales Analytics",
            icon=":material/query_stats:",
        ),
        st.Page(
            "pages/4_Demand_Forecast.py",
            title="Demand Forecast",
            icon=":material/trending_up:",
        ),
        st.Page(
            "pages/6_Model_Performance.py",
            title="Model Performance",
            icon=":material/monitoring:",
        ),
    ],
    "Support": [
        st.Page(
            "pages/7_About_Help.py",
            title="About & Help",
            icon=":material/help_outline:",
        ),
    ],
}

st.navigation(pages, position="sidebar").run()
