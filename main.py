import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="FinAgent",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    st.title("💸 FinAgent: Your AI Financial Assistant")
    
    st.sidebar.header("Navigation")
    app_mode = st.sidebar.selectbox("Choose the interaction mode",
        ["Dashboard", "Transaction Log", "Smart Ingest", "Settings"]
    )
    
    if app_mode == "Dashboard":
        st.header("Financial Overview")
        st.info("Welcome to FinAgent! Your personalized financial insights on autopilot.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Spent (This Month)", value="$0.00", delta="0%")
        with col2:
            st.metric(label="Most Active Category", value="N/A")
        with col3:
            st.metric(label="Upcoming Bills", value="0")

    elif app_mode == "Transaction Log":
        st.header("Transaction History")
        st.write("Connect to database to see transactions.")

    elif app_mode == "Smart Ingest":
        st.header("Upload Receipts or Paste Texts")
        
        tab1, tab2 = st.tabs(["Text Parse", "Image Upload"])
        
        with tab1:
            raw_text = st.text_area("Paste transaction email or SMS here:")
            if st.button("Parse Text"):
                st.warning("Ollama integration pending.")
                
        with tab2:
            uploaded_file = st.file_uploader("Choose a receipt image", type=["jpg", "png", "jpeg"])
            if uploaded_file is not None:
                st.image(uploaded_file, caption='Uploaded Receipt', use_column_width=True)
                st.warning("Vision processing pending.")

    elif app_mode == "Settings":
        st.header("Configuration")
        st.text_input("Ollama Base URL", value="http://localhost:11434")

if __name__ == "__main__":
    main()
