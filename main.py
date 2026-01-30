import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
import os
from src.core.parser import parse_transaction_text
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# For demo purposes - in production, this would come from Supabase Auth
DEMO_USER_ID = "c9254f2f-241d-45ce-81f7-cca4c02a3f19"

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
        ["Dashboard", "Transaction Log", "Smart Ingest", "Search", "Friends & Debts", "Settings"]
    )
    
    if app_mode == "Dashboard":
        st.header("Financial Overview")
        
        if not supabase:
            st.error("⚠️ Supabase not configured. Please check your .env file.")
            return
        
        try:
            # Fetch all transactions for the demo user
            response = supabase.table("transactions").select("*").eq("user_id", DEMO_USER_ID).execute()
            transactions_data = response.data
            
            if not transactions_data:
                st.info("No transactions found. Run the populate_synthetic_data.py script to add sample data.")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(transactions_data)
            df['date'] = pd.to_datetime(df['date'])
            df['amount'] = pd.to_numeric(df['amount'])
            
            # Calculate metrics
            today = datetime.now()
            first_day_of_month = today.replace(day=1)
            
            # This month's spending
            this_month = df[df['date'] >= pd.Timestamp(first_day_of_month)]
            total_this_month = this_month['amount'].sum()
            
            # Last month's spending for comparison
            last_month_start = (first_day_of_month - timedelta(days=1)).replace(day=1)
            last_month = df[(df['date'] >= pd.Timestamp(last_month_start)) & (df['date'] < pd.Timestamp(first_day_of_month))]
            total_last_month = last_month['amount'].sum() if not last_month.empty else total_this_month
            
            # Calculate percentage change
            if total_last_month > 0:
                pct_change = ((total_this_month - total_last_month) / total_last_month) * 100
            else:
                pct_change = 0
            
            # Most active category
            category_counts = df['category'].value_counts()
            most_active_category = category_counts.index[0] if not category_counts.empty else "N/A"
            
            # Fetch unpaid debts
            debts_response = supabase.table("debts").select("*").eq("user_id", DEMO_USER_ID).eq("is_paid", False).execute()
            unpaid_debts_count = len(debts_response.data)
            
            # Display Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label="Total Spent (This Month)", 
                    value=f"${total_this_month:,.2f}", 
                    delta=f"{pct_change:+.1f}%" if pct_change != 0 else None,
                    delta_color="inverse"
                )
            with col2:
                st.metric(label="Most Active Category", value=most_active_category)
            with col3:
                st.metric(label="Unpaid Debts", value=str(unpaid_debts_count))
            
            st.markdown("---")
            
            # Charts Row
            
            # Add time filter for charts
            chart_period = st.selectbox("Chart Time Period", ["This Month", "Last 30 Days", "Last 90 Days"])
            
            chart_col1, chart_col2 = st.columns(2)
            
            # Determine data based on filter
            if chart_period == "This Month":
                chart_data = this_month
            elif chart_period == "Last 30 Days":
                 start_date = today - timedelta(days=30)
                 chart_data = df[df['date'] >= pd.Timestamp(start_date)]
            else: # Last 90 Days
                 start_date = today - timedelta(days=90)
                 chart_data = df[df['date'] >= pd.Timestamp(start_date)]

            with chart_col1:
                st.subheader("📉 Spending Trend")
                # Group by date and sum amount
                daily_spending = chart_data.groupby('date')['amount'].sum().reset_index()
                
                if not daily_spending.empty:
                    fig_trend = px.line(
                        daily_spending, 
                        x='date', 
                        y='amount', 
                        markers=True,
                        labels={'amount': 'Amount ($)', 'date': 'Date'},
                        template="plotly_dark",
                        title=f"Spending - {chart_period}"
                    )
                    fig_trend.update_layout(xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("No spending data for this month.")

            with chart_col2:
                st.subheader("🍩 Category Breakdown")
                # Group by category
                category_spend = chart_data.groupby('category')['amount'].sum().reset_index()
                
                if not category_spend.empty:
                    fig_pie = px.pie(
                        category_spend, 
                        values='amount', 
                        names='category', 
                        hole=0.4,
                        template="plotly_dark"
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No category data available.")
            
            st.markdown("---")
            
            # Recent Activity
            st.subheader("Recent Activity")
            recent_transactions = df.sort_values('date', ascending=False).head(10)
            
            # Format for display
            display_df = recent_transactions[['date', 'merchant', 'amount', 'category', 'notes']].copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
            display_df.columns = ['Date', 'Merchant', 'Amount', 'Category', 'Notes']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Error loading dashboard data: {e}")

    elif app_mode == "Transaction Log":
        st.header("Transaction History")
        
        if not supabase:
            st.error("⚠️ Supabase not configured. Please check your .env file.")
            return
        
        try:
            # Fetch all transactions
            response = supabase.table("transactions").select("*").eq("user_id", DEMO_USER_ID).execute()
            transactions_data = response.data
            
            if not transactions_data:
                st.info("No transactions found. Run the populate_synthetic_data.py script to add sample data.")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(transactions_data)
            df['date'] = pd.to_datetime(df['date'])
            df['amount'] = pd.to_numeric(df['amount'])
            
            # Add filters
            col1, col2 = st.columns(2)
            
            with col1:
                # Category filter
                categories = ['All'] + sorted(df['category'].unique().tolist())
                selected_category = st.selectbox("Filter by Category", categories)
            
            with col2:
                # Date range filter
                date_range = st.selectbox(
                    "Date Range",
                    ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days"]
                )
            
            # Apply filters
            filtered_df = df.copy()
            
            if selected_category != 'All':
                filtered_df = filtered_df[filtered_df['category'] == selected_category]
            
            if date_range != "All Time":
                days_map = {
                    "Last 7 Days": 7,
                    "Last 30 Days": 30,
                    "Last 90 Days": 90
                }
                cutoff_date = datetime.now() - timedelta(days=days_map[date_range])
                filtered_df = filtered_df[filtered_df['date'] >= pd.Timestamp(cutoff_date)]
            
            # Sort by date (newest first)
            filtered_df = filtered_df.sort_values('date', ascending=False)
            
            # Display summary stats
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Transactions", len(filtered_df))
            with col2:
                st.metric("Total Amount", f"${filtered_df['amount'].sum():,.2f}")
            with col3:
                avg_amount = filtered_df['amount'].mean() if len(filtered_df) > 0 else 0
                st.metric("Average Amount", f"${avg_amount:,.2f}")
            
            st.markdown("---")
            
            # Format for display
            display_df = filtered_df[['date', 'merchant', 'amount', 'category', 'notes']].copy()
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
            display_df['notes'] = display_df['notes'].fillna('')
            display_df.columns = ['Date', 'Merchant', 'Amount', 'Category', 'Notes']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
            
        except Exception as e:
            st.error(f"Error loading transactions: {e}")

    elif app_mode == "Smart Ingest":
        st.header("Upload Receipts or Paste Texts")
        
        tab1, tab2 = st.tabs(["Text Parse", "Image Upload"])
        
        with tab1:
            st.subheader(" 📝 Paste Transaction Text")
            st.caption("Example: 'Spent $15.50 at Starbucks today for coffee' or 'Coffee at Starbucks for 15 and lunch at Subway for 8.50'")
            raw_text = st.text_area("Transaction input:", height=100, key="raw_input")
            
            if st.button("✨ Parse Text", type="primary"):
                if not raw_text:
                    st.error("Please enter some text.")
                else:
                    with st.spinner("Asking the AI..."):
                        result = parse_transaction_text(raw_text)
                    
                    if result:
                        # Check if multiple transactions or single
                        if isinstance(result, list):
                            st.session_state['parsed_transactions'] = result
                            st.session_state['is_multi'] = True
                            st.success(f"Found {len(result)} transactions!")
                        else:
                            st.session_state['parsed_transaction'] = result
                            st.session_state['is_multi'] = False
                            st.success("Parsed successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to parse transaction. Please check your Ollama connection.")
            
            # Handle multiple transactions
            if 'parsed_transactions' in st.session_state and st.session_state.get('is_multi'):
                transactions = st.session_state['parsed_transactions']
                
                st.markdown("---")
                st.subheader(f"📋 Review {len(transactions)} Transactions")
                
                # Display each transaction in an expander
                for idx, transaction in enumerate(transactions):
                    with st.expander(f"Transaction {idx+1}: {transaction.merchant} - ${transaction.amount:.2f}", expanded=(idx==0)):
                        with st.form(f"multi_transaction_form_{idx}"):
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                merchant = st.text_input("Merchant", value=transaction.merchant, key=f"merchant_{idx}")
                                amount = st.number_input("Amount", value=float(transaction.amount), min_value=0.01, step=0.01, key=f"amount_{idx}")
                                
                                # Handle date parsing
                                try:
                                    date_value = pd.to_datetime(transaction.date).date()
                                except:
                                    date_value = datetime.now().date()
                                
                                transaction_date = st.date_input("Date", value=date_value, key=f"date_{idx}")
                            
                            with col_b:
                                category = st.text_input("Category", value=transaction.category or "", key=f"category_{idx}")
                                notes = st.text_area("Notes", value=transaction.notes or "", height=100, key=f"notes_{idx}")
                            
                            if st.form_submit_button(f"💾 Save Transaction {idx+1}", type="primary"):
                                if not supabase:
                                    st.error("⚠️ Supabase not configured.")
                                else:
                                    try:
                                        transaction_data = {
                                            "user_id": DEMO_USER_ID,
                                            "date": transaction_date.isoformat(),
                                            "amount": amount,
                                            "merchant": merchant,
                                            "category": category if category else None,
                                            "notes": notes if notes else None,
                                        }
                                        
                                        supabase.table("transactions").insert(transaction_data).execute()
                                        st.success(f"✅ Saved {merchant}!")
                                        
                                        # Remove this transaction from the list
                                        transactions.pop(idx)
                                        if not transactions:
                                            del st.session_state['parsed_transactions']
                                            del st.session_state['is_multi']
                                        st.rerun()
                                        
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                
                # Batch save all button
                if st.button("💾 Save All Transactions", type="secondary"):
                    if not supabase:
                        st.error("⚠️ Supabase not configured.")
                    else:
                        try:
                            saved_count = 0
                            for transaction in transactions:
                                transaction_data = {
                                    "user_id": DEMO_USER_ID,
                                    "date": transaction.date,
                                    "amount": float(transaction.amount),
                                    "merchant": transaction.merchant,
                                    "category": transaction.category,
                                    "notes": transaction.notes,
                                }
                                supabase.table("transactions").insert(transaction_data).execute()
                                saved_count += 1
                            
                            st.success(f"✅ Saved all {saved_count} transactions!")
                            del st.session_state['parsed_transactions']
                            del st.session_state['is_multi']
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                if st.button("❌ Cancel All"):
                    del st.session_state['parsed_transactions']
                    del st.session_state['is_multi']
                    st.rerun()
            
            # Display single transaction form
            elif 'parsed_transaction' in st.session_state and not st.session_state.get('is_multi'):
                transaction = st.session_state['parsed_transaction']
                
                st.markdown("---")
                st.subheader("Review & Edit Transaction")
                
                # Show split breakdown if applicable
                if transaction.is_split and transaction.split_with:
                    st.info(f"💰 Split with: {', '.join(transaction.split_with)}")
                    
                    if transaction.my_share is not None:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Your Share", f"${transaction.my_share:.2f}")
                        with col2:
                            if transaction.split_amounts:
                                for name, amt in transaction.split_amounts.items():
                                    st.metric(f"{name}'s Share", f"${amt:.2f}")
                
                # Create editable form
                with st.form("transaction_form"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        merchant = st.text_input("Merchant", value=transaction.merchant)
                        amount = st.number_input("Amount", value=float(transaction.amount), min_value=0.01, step=0.01)
                        
                        # Handle date parsing
                        try:
                            if transaction.date.lower() in ['today', 'now']:
                                date_value = datetime.now().date()
                            elif transaction.date.lower() == 'yesterday':
                                date_value = (datetime.now() - timedelta(days=1)).date()
                            else:
                                date_value = pd.to_datetime(transaction.date).date()
                        except:
                            date_value = datetime.now().date()
                        
                        transaction_date = st.date_input("Date", value=date_value)
                    
                    with col_b:
                        category = st.text_input("Category", value=transaction.category or "")
                        notes = st.text_area("Notes", value=transaction.notes or "", height=100)
                    
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        save_button = st.form_submit_button("💾 Save to Database", type="primary")
                    with col2:
                        cancel_button = st.form_submit_button("❌ Cancel")
                    
                    if save_button:
                        if not supabase:
                            st.error("⚠️ Supabase not configured. Please check your .env file.")
                        else:
                            try:
                                # Prepare transaction data
                                transaction_data = {
                                    "user_id": DEMO_USER_ID,
                                    "date": transaction_date.isoformat(),
                                    "amount": amount,
                                    "merchant": merchant,
                                    "category": category if category else None,
                                    "notes": notes if notes else None,
                                }
                                
                                # Insert into database
                                tx_response = supabase.table("transactions").insert(transaction_data).execute()
                                
                                # Handle splitting logic with UNEVEN split support
                                if hasattr(transaction, 'is_split') and transaction.is_split and transaction.split_with:
                                    # Fetch existing friends
                                    friends_res = supabase.table("friends").select("*").eq("user_id", DEMO_USER_ID).execute()
                                    existing_friends = {f['name'].lower(): f['id'] for f in friends_res.data}
                                    
                                    # Use split_amounts if available, otherwise calculate evenly
                                    if transaction.split_amounts:
                                        # Uneven split - use individual amounts
                                        for friend_name, friend_amount in transaction.split_amounts.items():
                                            fname_lower = friend_name.lower()
                                            friend_id = existing_friends.get(fname_lower)
                                            
                                            # Create friend if not exists
                                            if not friend_id:
                                                new_friend = supabase.table("friends").insert({
                                                    "user_id": DEMO_USER_ID, 
                                                    "name": friend_name
                                                }).execute()
                                                friend_id = new_friend.data[0]['id']
                                            
                                            # Add debt with specific amount
                                            supabase.table("debts").insert({
                                                "user_id": DEMO_USER_ID,
                                                "friend_id": friend_id,
                                                "amount": friend_amount,
                                                "description": f"Split {merchant} bill",
                                                "is_paid": False
                                            }).execute()
                                            st.toast(f"Added debt for {friend_name} (${friend_amount:.2f})")
                                    else:
                                        # Even split - calculate equally
                                        split_count = len(transaction.split_with) + 1  # +1 for you
                                        split_amount = amount / split_count
                                        
                                        for friend_name in transaction.split_with:
                                            fname_lower = friend_name.lower()
                                            friend_id = existing_friends.get(fname_lower)
                                            
                                            # Create friend if not exists
                                            if not friend_id:
                                                new_friend = supabase.table("friends").insert({
                                                    "user_id": DEMO_USER_ID, 
                                                    "name": friend_name
                                                }).execute()
                                                friend_id = new_friend.data[0]['id']
                                            
                                            # Add debt
                                            supabase.table("debts").insert({
                                                "user_id": DEMO_USER_ID,
                                                "friend_id": friend_id,
                                                "amount": split_amount,
                                                "description": f"Split {merchant} bill",
                                                "is_paid": False
                                            }).execute()
                                            st.toast(f"Added debt for {friend_name} (${split_amount:.2f})")
                                
                                st.success(f"✅ Transaction saved! Added ${amount:.2f} at {merchant}")
                                
                                # Clear session state
                                del st.session_state['parsed_transaction']
                                if 'is_multi' in st.session_state:
                                    del st.session_state['is_multi']
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error saving transaction: {e}")
                    
                    if cancel_button:
                        # Clear session state
                        del st.session_state['parsed_transaction']
                        if 'is_multi' in st.session_state:
                            del st.session_state['is_multi']
                        st.rerun()

        with tab2:
            st.subheader("📸 Receipt Scanner")
            uploaded_file = st.file_uploader("Choose a receipt image", type=["jpg", "png", "jpeg"])
            
            if uploaded_file is not None:
                # Display image
                st.image(uploaded_file, caption='Uploaded Receipt', width=300)
                
                if st.button("🔍 Analyze Receipt", type="primary"):
                    with st.spinner("Analyzing receipt with Vision AI..."):
                        # Get bytes from uploaded file
                        bytes_data = uploaded_file.getvalue()
                        
                        # Lazy import
                        from src.core.llm import extract_receipt_data
                        
                        # Extract data
                        transaction = extract_receipt_data(bytes_data)
                        
                        if transaction:
                            st.session_state['parsed_transaction'] = transaction
                            st.success("Receipt analyzed successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to analyze receipt.")

    elif app_mode == "Friends & Debts":
        st.header("Friends & Bill Splitting 💸")
        
        if not supabase:
            st.error("⚠️ Supabase not configured. Please check your .env file.")
            return

        # Fetch friends
        try:
            friends_response = supabase.table("friends").select("*").eq("user_id", DEMO_USER_ID).execute()
            friends = friends_response.data
            friends_dict = {f['id']: f['name'] for f in friends}
        except Exception as e:
            st.error(f"Error fetching friends: {e}")
            friends = []
            friends_dict = {}
        
        # Fetch debts
        try:
            debts_response = supabase.table("debts").select("*").eq("user_id", DEMO_USER_ID).execute()
            debts = debts_response.data
        except Exception as e:
            st.error(f"Error fetching debts: {e}")
            debts = []
        
        # Calculate totals
        total_owed = sum(d['amount'] for d in debts if not d['is_paid'])
        active_friends = len(set(d['friend_id'] for d in debts if not d['is_paid']))
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Outstanding", f"${total_owed:,.2f}", help="Money friends owe you")
        with col2:
            st.metric("Friends with Debts", active_friends)
        with col3:
            st.metric("Total Friends", len(friends))
            
        st.markdown("---")
            
        tab1, tab2 = st.tabs(["💰 Manage Debts", "👥 Manage Friends"])
        
        with tab1:
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.subheader("Active Debts")
                unpaid_debts = [d for d in debts if not d['is_paid']]
                
                if not unpaid_debts:
                    st.info("🎉 No active debts! You're all settled up.")
                else:
                    for debt in unpaid_debts:
                        friend_name = friends_dict.get(debt['friend_id'], 'Unknown Friend')
                        with st.expander(f"**{friend_name}** owes **${debt['amount']:.2f}**"):
                            st.write(f"📝 **For:** {debt.get('description', 'No description')}")
                            st.caption(f"📅 Added on: {pd.to_datetime(debt['created_at']).strftime('%Y-%m-%d')}")
                            
                            if st.button("✅ Mark as Paid", key=f"pay_{debt['id']}"):
                                try:
                                    supabase.table("debts").update({"is_paid": True}).eq("id", debt['id']).execute()
                                    st.success(f"Marked debt from {friend_name} as paid!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating debt: {e}")

            with col_b:
                st.subheader("➕ Split a Bill")
                with st.form("add_debt_form"):
                    if not friends:
                        st.warning("Add friends first to split bills!")
                        st.form_submit_button("Add Debt", disabled=True)
                    else:
                        friend_id = st.selectbox("Select Friend", options=friends_dict.keys(), format_func=lambda x: friends_dict[x])
                        amount = st.number_input("Amount ($)", min_value=0.01, step=1.00)
                        desc = st.text_input("Description (e.g. Lunch)")
                        
                        if st.form_submit_button("Add Debt", type="primary"):
                            if amount > 0 and desc:
                                try:
                                    supabase.table("debts").insert({
                                        "user_id": DEMO_USER_ID,
                                        "friend_id": friend_id,
                                        "amount": amount,
                                        "description": desc,
                                        "is_paid": False
                                    }).execute()
                                    st.success("Debt added successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error adding debt: {e}")
                            else:
                                st.error("Please enter amount and description.")

        with tab2:
            col_a, col_b = st.columns([2, 1])
            
            with col_a:
                st.subheader("Your Friends")
                if not friends:
                    st.info("No friends added yet.")
                else:
                    for f in friends:
                        st.info(f"👤 **{f['name']}**  \n📞 {f.get('phone', 'No phone')}")
            
            with col_b:
                st.subheader("➕ Add New Friend")
                with st.form("add_friend_form"):
                    name = st.text_input("Name")
                    phone = st.text_input("Phone (Optional)")
                    
                    if st.form_submit_button("Add Friend", type="primary"):
                        if name:
                            try:
                                supabase.table("friends").insert({
                                    "user_id": DEMO_USER_ID,
                                    "name": name,
                                    "phone": phone
                                }).execute()
                                st.success(f"Added {name}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding friend: {e}")
                        else:
                            st.error("Name is required.")

    elif app_mode == "Search":
        st.header("🔍 Semantic Transaction Search")
        st.markdown("Search your transactions using natural language! Try 'coffee with friends' or 'gym membership'.")
        
    elif app_mode == "Search":
        st.header("🔍 Semantic Transaction Search")
        st.markdown("Search your transactions using natural language! Try 'coffee with friends' or 'gym membership'.")
        
        with st.form("search_form"):
            query = st.text_input("Search Query", placeholder="e.g., 'Groceries from last week'")
            submitted = st.form_submit_button("Search")
            
            if submitted and query:
                with st.spinner("Searching..."):
                    try:
                        # Lazy import to avoid circular dependency issues if any
                        from src.core.embeddings import generate_embedding
                        
                        query_embedding = generate_embedding(query)
                        
                        response = supabase.rpc("match_transactions", {
                            "query_embedding": query_embedding,
                            "match_threshold": 0.5,
                            "match_count": 10,
                            "p_user_id": DEMO_USER_ID
                        }).execute()
                        
                        results = response.data
                        
                        if not results:
                            st.info("No matching transactions found.")
                        else:
                            for tx in results:
                                st.markdown(f"""
                                **{tx['merchant']}** - {tx['category']}  
                                {tx['notes'] or 'No notes'}  
                                **${tx['amount']:.2f}** | {tx['date']}
                                """)
                                st.divider()
                                    
                    except Exception as e:
                        st.error(f"Search failed: {e}")
                    st.info("💡 Note: Ensure you have populated embeddings by running the backfill script and created the 'match_transactions' function in Supabase.")

    elif app_mode == "Settings":
        st.header("Configuration")
        st.text_input("Ollama Base URL", value=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        st.text_input("Supabase URL", value=os.environ.get("SUPABASE_URL", ""))

if __name__ == "__main__":
    main()
