import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
import os
from src.core.parser import parse_transaction_text
from src.core.currency_converter import convert_currency, get_currency_symbol, format_amount, CURRENCY_SYMBOLS
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
    
    # Sidebar
    with st.sidebar:
        st.title("💸 FinAgent")
        st.caption("Your Personal Finance AI Assistant")
        st.markdown("---")
        
        # Navigation
        app_mode = st.radio(
            "Navigate",
            ["📊 Dashboard", "📝 Transaction Log", "🧠 Smart Ingest", "🔎 Search", "🤝 Friends & Debts", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Settings
        with st.expander("⚙️ Settings", expanded=True): # Expanded by default for demo
            # Native currency preference
            st.subheader("Currency Preferences")
            native_currency = st.selectbox(
                "Your Native Currency",
                options=list(CURRENCY_SYMBOLS.keys()),
                index=list(CURRENCY_SYMBOLS.keys()).index("SGD"), # Default to SGD for demo
                help="All amounts will show conversion to this currency"
            )
            st.session_state['native_currency'] = native_currency
            
            st.caption(f"Symbol: {CURRENCY_SYMBOLS[native_currency]}")
    
    if app_mode == "📊 Dashboard":
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
            df['original_amount'] = df['amount'].copy()  # Store original amount for display
            
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
            
            # Financial Insights Section
            with st.expander("📊 Spending Analysis & Recommendations", expanded=False):
                st.caption("Professional analysis comparing your spending patterns to population benchmarks")
                
                # Check cache for recommendations
                cache_key = f"recommendations_{DEMO_USER_ID}_{chart_period}_{native_currency}"
                cache_valid = False
                
                if cache_key in st.session_state:
                    cache_data = st.session_state[cache_key]
                    cache_time = cache_data.get('timestamp')
                    if cache_time and (datetime.now() - cache_time).total_seconds() < 86400:  # 24 hours
                        cache_valid = True
                
                if cache_valid:
                    # Use cached data
                    comparison_data = st.session_state[cache_key]['comparison']
                    recommendations_text = st.session_state[cache_key]['recommendations']
                else:
                    # Calculate fresh data
                    with st.spinner("Analyzing your spending patterns..."):
                        try:
                            from src.core.spending_analytics import (
                                calculate_user_spending_by_category,
                                calculate_population_averages,
                                compare_user_to_population,
                                get_top_overspending_categories,
                                get_top_underspending_categories
                            )
                            from src.core.llm import generate_financial_recommendations
                            
                            # Determine time period in days
                            if chart_period == "This Month":
                                days = (datetime.now() - first_day_of_month).days + 1
                            elif chart_period == "Last 30 Days":
                                days = 30
                            else:  # Last 90 Days
                                days = 90
                            
                            # Calculate spending data
                            user_spending = calculate_user_spending_by_category(
                                supabase, DEMO_USER_ID, days, native_currency
                            )
                            
                            population_avg = calculate_population_averages(
                                supabase, days, native_currency, exclude_user_id=DEMO_USER_ID
                            )
                            
                            if user_spending and population_avg:
                                comparison = compare_user_to_population(user_spending, population_avg)
                                overspending = get_top_overspending_categories(comparison, limit=3)
                                underspending = get_top_underspending_categories(comparison, limit=3)
                                
                                # Generate AI recommendations
                                currency_symbol = get_currency_symbol(native_currency)
                                recommendations_text = generate_financial_recommendations(
                                    user_spending,
                                    population_avg,
                                    overspending,
                                    underspending,
                                    currency_symbol
                                )
                                
                                # Cache the results
                                st.session_state[cache_key] = {
                                    'timestamp': datetime.now(),
                                    'comparison': comparison,
                                    'recommendations': recommendations_text,
                                    'user_spending': user_spending,
                                    'population_avg': population_avg
                                }
                                
                                comparison_data = comparison
                            else:
                                comparison_data = None
                                recommendations_text = "Not enough data to generate recommendations. Add more transactions or check back later."
                        
                        except Exception as e:
                            st.error(f"Error generating insights: {e}")
                            comparison_data = None
                            recommendations_text = "Unable to generate recommendations at this time."
                
                if comparison_data:
                    # Create comparison bar chart
                    user_spending = st.session_state[cache_key].get('user_spending', {})
                    population_avg = st.session_state[cache_key].get('population_avg', {})
                    
                    # Prepare data for chart
                    categories = list(set(user_spending.keys()) | set(population_avg.keys()))
                    chart_data = []
                    
                    for category in categories:
                        user_amt = user_spending.get(category, 0)
                        pop_amt = population_avg.get(category, 0)
                        
                        chart_data.append({
                            'Category': category,
                            'Your Spending': user_amt,
                            'Population Average': pop_amt
                        })
                    
                    if chart_data:
                        chart_df = pd.DataFrame(chart_data)
                        
                        # Create grouped bar chart
                        fig_comparison = px.bar(
                            chart_df,
                            x='Category',
                            y=['Your Spending', 'Population Average'],
                            barmode='group',
                            title=f"Spending Comparison - {chart_period}",
                            labels={'value': f'Amount ({native_currency})', 'variable': 'Type'},
                            template="plotly_dark",
                            color_discrete_map={
                                'Your Spending': '#FF6B6B',
                                'Population Average': '#4ECDC4'
                            }
                        )
                        
                        # Get currency symbol for formatting
                        curr_symbol = get_currency_symbol(native_currency)
                        
                        fig_comparison.update_layout(
                            xaxis_title=None,
                            yaxis_title=f'Amount ({native_currency})',
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            height=500,  # Increase height for better readability
                            xaxis=dict(
                                tickangle=-45  # Rotate category labels for better fit
                            ),
                            yaxis=dict(
                                tickformat=f'{curr_symbol},.0f',  # Format with currency symbol and commas
                                separatethousands=True
                            ),
                            hoverlabel=dict(
                                bgcolor="white",
                                font_size=14,
                                font_family="Arial"
                            )
                        )
                        
                        # Update hover template for better number display
                        fig_comparison.update_traces(
                            hovertemplate='<b>%{x}</b><br>%{fullData.name}: ' + curr_symbol + '%{y:,.2f}<extra></extra>'
                        )
                        
                        st.plotly_chart(fig_comparison, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # Display AI recommendations
                        st.subheader("Analysis & Recommendations")
                        st.markdown(recommendations_text)
                        
                        st.caption(f"*Analysis based on {chart_period.lower()} spending patterns. Updated daily.*")
                    else:
                        st.info("Not enough spending data to compare.")
                else:
                    st.info("Add more transactions to see personalized recommendations.")
            
            st.markdown("---")
            
            # Recent Activity
            st.subheader("Recent Activity")
            recent_transactions = df.sort_values('date', ascending=False).head(10)
            
            # Format for display
            display_df = recent_transactions[['date', 'merchant', 'original_amount', 'amount', 'category', 'notes']].copy()
            if 'currency' in recent_transactions.columns:
                display_df['currency'] = recent_transactions['currency']
            else:
                display_df['currency'] = 'SGD'
            
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            
            # Format amounts with proper symbols
            def format_with_currency(row):
                orig_symbol = get_currency_symbol(row.get('currency', 'SGD'))
                native_symbol = get_currency_symbol(native_currency)
                orig_amt = row['original_amount']
                conv_amt = row['amount']
                
                if row.get('currency', 'SGD') == native_currency:
                    return f"{orig_symbol}{orig_amt:,.2f}"
                else:
                    return f"{native_symbol}{conv_amt:,.2f} ({orig_symbol}{orig_amt:,.2f})"
            
            display_df['amount_display'] = display_df.apply(format_with_currency, axis=1)
            display_df = display_df[['date', 'merchant', 'amount_display', 'category', 'notes']]
            display_df.columns = ['Date', 'Merchant', 'Amount', 'Category', 'Notes']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Error loading dashboard data: {e}")

    elif app_mode == "📝 Transaction Log":
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
            # Store original amounts before conversion
            df['original_amount'] = pd.to_numeric(df['amount']) # Store original numeric amount
            df['amount'] = pd.to_numeric(df['amount']) # Convert 'amount' to numeric for calculations
            
            # Add converted amounts
            native_currency = st.session_state.get('native_currency', 'SGD')
            
            def convert_amount_to_native(row):
                original_currency = row.get('currency', 'SGD')
                original_amount = row['original_amount']
                
                if original_currency == native_currency:
                    return original_amount
                
                try:
                    converted = convert_currency(original_amount, original_currency, native_currency)
                    return converted if converted else original_amount
                except:
                    return original_amount
            
            df['amount'] = df.apply(convert_amount_to_native, axis=1)
            
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
            
            currency_symbol = get_currency_symbol(native_currency)
            
            with col1:
                st.metric("Total Transactions", len(filtered_df))
            with col2:
                st.metric("Total Amount", f"{currency_symbol}{filtered_df['amount'].sum():,.2f}")
            with col3:
                avg_amount = filtered_df['amount'].mean() if len(filtered_df) > 0 else 0
                st.metric("Average Amount", f"{currency_symbol}{avg_amount:,.2f}")
            
            st.markdown("---")
            
            # Format for display
            display_df = filtered_df[['date', 'merchant', 'original_amount', 'amount', 'category', 'notes']].copy()
            if 'currency' in filtered_df.columns:
                display_df['currency'] = filtered_df['currency']
            else:
                display_df['currency'] = 'SGD'
            
            display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
            
            # Format amounts with currency conversion display
            def format_with_currency(row):
                orig_symbol = get_currency_symbol(row.get('currency', 'SGD'))
                native_symbol = get_currency_symbol(native_currency)
                orig_amt = row['original_amount']
                conv_amt = row['amount']
                
                if row.get('currency', 'SGD') == native_currency:
                    return f"{orig_symbol}{orig_amt:,.2f}"
                else:
                    return f"{native_symbol}{conv_amt:,.2f} ({orig_symbol}{orig_amt:,.2f})"
            
            display_df['amount_display'] = display_df.apply(format_with_currency, axis=1)
            display_df['notes'] = display_df['notes'].fillna('')
            display_df = display_df[['date', 'merchant', 'amount_display', 'category', 'notes']]
            display_df.columns = ['Date', 'Merchant', 'Amount', 'Category', 'Notes']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
            
        except Exception as e:
            st.error(f"Error loading transactions: {e}")

    elif app_mode == "🧠 Smart Ingest":
        st.header("📝 Smart Transaction Ingest")
        st.caption("Parse transactions from text or receipt images")
        
        # Input method selection dropdown
        input_method = st.selectbox(
            "Choose input method:",
            ["📝 Text Input", "📸 Receipt Upload"],
            key="input_method_selector",
            help="Select how you want to add transactions"
        )
        
        st.markdown("---")
        
        # Show selected input method
        if input_method == "📝 Text Input":
            st.subheader("Text Input")
            st.caption("Example: 'Spent $15.50 at Starbucks' or 'Dinner $90 split with Alice'")
            
            raw_text = st.text_area(
                "Transaction text:", 
                height=150, 
                key="raw_input", 
                placeholder="Paste your transaction description here...\n\nExamples:\n- 'Coffee at Starbucks for $15'\n- 'Split $60 dinner with Alice and Bob'\n- 'Lunch $12 at Subway and coffee $5 at Peets'"
            )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                parse_button = st.button("✨ Parse Text", type="primary", use_container_width=True)
            
            if parse_button:
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
                            st.success(f"✅ Found {len(result)} transactions!")
                        else:
                            st.session_state['parsed_transaction'] = result
                            st.session_state['is_multi'] = False
                            st.success("✅ Parsed successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to parse transaction. Please check your Ollama connection.")
        
        else:  # Receipt Upload
            st.subheader("Receipt Upload")
            st.caption("Upload a receipt image for AI-powered analysis")
            
            uploaded_file = st.file_uploader(
                "Choose receipt image", 
                type=["jpg", "png", "jpeg"],
                help="Supported formats: JPG, PNG, JPEG"
            )
            
            if uploaded_file is not None:
                # Show image preview in collapsed expander
                with st.expander("📷 Receipt Preview", expanded=False):
                    st.image(uploaded_file, caption='Receipt Preview', width=300)
                
                # Optional context input
                st.markdown("**Optional Context**")
                st.caption("Help the AI understand bill splitting or other details")
                receipt_context = st.text_area(
                    "Additional context:",
                    placeholder="Examples:\n- 'Split with Alice and Bob'\n- 'My share is 60%'\n- 'I paid for drinks only'",
                    height=120,
                    key="receipt_context",
                    label_visibility="collapsed"
                )
                
                analyze_button = st.button("🔍 Analyze Receipt", type="primary", use_container_width=True)
                
                if analyze_button:
                    with st.spinner("Analyzing receipt with Vision AI..."):
                        # Get bytes from uploaded file
                        bytes_data = uploaded_file.getvalue()
                        
                        # Lazy import
                        from src.core.llm import extract_receipt_data
                        
                        # Extract data with optional context
                        transaction = extract_receipt_data(bytes_data, context=receipt_context if receipt_context else None)
                        
                        if transaction:
                            st.session_state['parsed_transaction'] = transaction
                            st.session_state['is_multi'] = False
                            st.success("✅ Receipt analyzed successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to analyze receipt.")
        
        st.markdown("---")
        
        # Shared transaction review section (works for both text and image)
        
        # Handle multiple transactions
        if 'parsed_transactions' in st.session_state and st.session_state.get('is_multi'):
            transactions = st.session_state['parsed_transactions']
            
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
                            try:
                                date_value = pd.to_datetime(transaction.date).date()
                            except:
                                date_value = datetime.now().date()
                            
                            transaction_data = {
                                "user_id": DEMO_USER_ID,
                                "date": date_value.isoformat(),
                                "amount": float(transaction.amount),
                                "merchant": transaction.merchant,
                                "category": transaction.category if transaction.category else None,
                                "notes": transaction.notes if transaction.notes else None,
                            }
                            
                            supabase.table("transactions").insert(transaction_data).execute()
                            saved_count += 1
                        
                        st.success(f"✅ Saved {saved_count} transactions!")
                        del st.session_state['parsed_transactions']
                        del st.session_state['is_multi']
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error saving batch: {e}")
        
        # Handle single transaction (works for both text and image!)
        elif 'parsed_transaction' in st.session_state and not st.session_state.get('is_multi'):
            transaction = st.session_state['parsed_transaction']
            # Transaction review section
            st.subheader("✨ Review Parsed Transaction")
            
            # Display merchant and date info
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**🏪 {transaction.merchant}**")
            with col2:
                st.markdown(f"📅 {transaction.date}")
            
            # Currency and amount display
            st.markdown("---")
            col_curr, col_amt = st.columns([1, 2])
            
            with col_curr:
                # Currency selector
                bill_currency = st.selectbox(
                    "Currency",
                    options=list(CURRENCY_SYMBOLS.keys()),
                    index=list(CURRENCY_SYMBOLS.keys()).index(transaction.currency or "SGD"),
                    key="bill_currency"
                )
                transaction.currency = bill_currency
            
            with col_amt:
                # Show amount with conversion
                native_curr = st.session_state.get('native_currency', 'SGD')
                
                # Format original amount
                original_display = format_amount(transaction.amount, bill_currency)
                st.metric("Total Amount", original_display)
                
                # Show conversion if different currency
                if bill_currency != native_curr:
                    converted = convert_currency(transaction.amount, bill_currency, native_curr)
                    if converted:
                        converted_display = format_amount(converted, native_curr)
                        st.caption(f"≈ {converted_display} ({native_curr})")
                    else:
                        st.caption(f"⚠️ Conversion unavailable")
            
            # Category and notes
            if transaction.category:
                st.caption(f"📂 Category: {transaction.category}")
            if transaction.notes:
                with st.expander("📝 Notes"):
                    st.write(transaction.notes)
            
            # Show split breakdown if applicable
            if transaction.is_split and transaction.split_with:
                print(f"\n[UI DEBUG] Split calculation:")
                print(f"  split_amounts exists: {transaction.split_amounts is not None}")
                print(f"  split_amounts value: {transaction.split_amounts}")
                print(f"  split_amounts length: {len(transaction.split_amounts) if transaction.split_amounts else 0}")
                
                # Calculate split amounts if not already provided
                if not transaction.split_amounts or len(transaction.split_amounts) == 0:
                    print(f"  [UI DEBUG] Using EQUAL SPLIT (no split_amounts from LLM)")
                    # Equal split as fallback
                    num_people = len(transaction.split_with) + 1  # +1 for user
                    per_person = transaction.amount / num_people
                    split_display = {name: per_person for name in transaction.split_with}
                    my_share = per_person
                else:
                    print(f"  [UI DEBUG] Using ITEM-BASED SPLIT (split_amounts from LLM)")
                    split_display = transaction.split_amounts.copy()  # Make a copy to modify
                    
                    # Add GST equally to each person if GST exists
                    num_people = len(transaction.split_with) + 1  # +1 for user
                    if transaction.gst and transaction.gst > 0:
                        gst_per_person = transaction.gst / num_people
                        st.caption(f"📊 GST (${transaction.gst:.2f}) split equally: ${gst_per_person:.2f} per person")
                        
                        # Add GST share to each person's amount
                        for name in split_display:
                            split_display[name] += gst_per_person
                    
                    # Calculate user's share as remainder
                    others_total = sum(split_display.values())
                    # Ensure user share is never negative, use max to handle rounding errors
                    my_share = max(0.01, transaction.amount - others_total)
                    
                    # If others_total exceeds transaction.amount, do equal split instead
                    if others_total > transaction.amount * 1.05:  # 5% tolerance
                        st.warning("⚠️ Detected amounts exceed total. Using equal split instead.")
                        num_people = len(transaction.split_with) + 1
                        per_person = transaction.amount / num_people
                        split_display = {name: per_person for name in transaction.split_with}
                        my_share = per_person

                
                # Show split breakdown in an expander
                with st.expander("💰 Split Breakdown", expanded=True):
                    st.caption(f"Total: ${transaction.amount:.2f}")
                    
                    # Show GST info if available
                    if transaction.gst and transaction.gst > 0:
                        st.caption(f"🧾 GST: ${transaction.gst:.2f} (split equally)")
                    
                    st.markdown("---")
                    st.subheader("✏️ Edit Split Amounts")
                    st.caption("Adjust amounts for each person. Total must equal bill amount.")
                    
                    # Create editable inputs for each person
                    edited_amounts = {}
                    
                    bill_curr = transaction.currency or "SGD"
                    native_curr = st.session_state.get('native_currency', 'SGD')
                    show_conversion = bill_curr != native_curr
                    
                    for name in transaction.split_with:
                        default_amount = split_display.get(name, 0)
                        col1, col2, col3 = st.columns([2, 2, 2]) if show_conversion else st.columns([3, 2, 1])
                        
                        with col1:
                            st.write(f"**{name}**")
                        with col2:
                            edited_amounts[name] = st.number_input(
                                f"Amount for {name}",
                                min_value=0.0,
                                value=float(default_amount),
                                step=0.01,
                                format="%.2f",
                                key=f"amount_input_{name}",
                                label_visibility="collapsed"
                            )
                        
                        if show_conversion:
                            with col3:
                                converted = convert_currency(edited_amounts[name], bill_curr, native_curr)
                                if converted:
                                    st.caption(f"≈ {format_amount(converted, native_curr)}")
                    
                    # User's share input
                    col1, col2, col3 = st.columns([2, 2, 2]) if show_conversion else st.columns([3, 2, 1])
                    with col1:
                        st.write("**You (remaining)**")
                    with col2:
                        user_amount = st.number_input(
                            "Your amount",
                            min_value=0.0,
                            value=float(my_share),
                            step=0.01,
                            format="%.2f",
                            key="amount_input_user",
                            label_visibility="collapsed"
                        )
                    
                    if show_conversion:
                        with col3:
                            converted_user = convert_currency(user_amount, bill_curr, native_curr)
                            if converted_user:
                                st.caption(f"≈ {format_amount(converted_user, native_curr)}")
                    
                    # Validation
                    total_split = sum(edited_amounts.values()) + user_amount
                    difference = abs(total_split - transaction.amount)
                    
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Split Total", f"${total_split:.2f}")
                    with col2:
                        st.metric("Bill Total", f"${transaction.amount:.2f}")
                    with col3:
                        if difference < 0.01:
                            st.success("✅ Match!")
                        else:
                            st.error(f"❌ Off by ${difference:.2f}")
                    
                    # Update split_display with edited values
                    split_display = edited_amounts
                    my_share = user_amount
                    
                    # Store validation status
                    st.session_state['split_valid'] = difference < 0.01

                
                # Friend selection UI - individual dropdowns for each person
                st.markdown("---")
                st.subheader("👥 Map People to Friends")
                st.caption("Select which friend each detected person corresponds to")
                
                # Initialize variables
                person_friend_mapping = {}
                
                if supabase:
                    # Fetch existing friends
                    try:
                        friends_res = supabase.table("friends").select("*").eq("user_id", DEMO_USER_ID).execute()
                        existing_friends = {f['name']: f['id'] for f in friends_res.data}
                        friend_names = list(existing_friends.keys())
                    except Exception as e:
                        st.error(f"Error fetching friends: {e}")
                        existing_friends = {}
                        friend_names = []
                    
                    # Fuzzy name matching for suggestions
                    from difflib import get_close_matches
                    
                    # Create individual dropdown for each detected person
                    
                    for detected_name in transaction.split_with:
                        amount = split_display.get(detected_name, transaction.amount / (len(transaction.split_with) + 1))
                        
                        col1, col2, col3 = st.columns([2, 3, 1])
                        
                        with col1:
                            st.write(f"**{detected_name}**")
                        
                        with col2:
                            # Try fuzzy match
                            matches = get_close_matches(detected_name, friend_names, n=1, cutoff=0.6)
                            default_friend = matches[0] if matches else None
                            
                            # Dropdown with "Add New" option
                            options = friend_names + [f"➕ Add '{detected_name}' as new friend"]
                            default_index = friend_names.index(default_friend) if default_friend else len(friend_names)
                            
                            selected = st.selectbox(
                                f"Friend for {detected_name}",
                                options=options,
                                index=default_index,
                                key=f"friend_select_{detected_name}",
                                label_visibility="collapsed"
                            )
                            
                            # Determine final friend name
                            if selected.startswith("➕"):
                                final_friend = detected_name
                            else:
                                final_friend = selected
                            
                            person_friend_mapping[detected_name] = final_friend
                         
                        with col3:
                            st.write(f"${amount:.2f}")
                     
                    # Store mapping and related data in session state for save handler
                    st.session_state['person_friend_mapping'] = person_friend_mapping
                    st.session_state['split_display'] = split_display
                    st.session_state['existing_friends'] = existing_friends
            
                    # Show summary
                    if person_friend_mapping:
                        st.success(f"✅ Mapped {len(person_friend_mapping)} people to friends")
                else:
                    st.warning("Supabase not configured - friend selection unavailable")
                    # Still initialize session state with empty values to prevent errors
                    st.session_state['person_friend_mapping'] = {}
                    st.session_state['split_display'] = split_display
                    st.session_state['existing_friends'] = {}
            
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
                        # Validate split amounts if this is a split transaction
                        if hasattr(transaction, 'is_split') and transaction.is_split:
                            split_valid = st.session_state.get('split_valid', True)
                            if not split_valid:
                                st.error("❌ Cannot save: Split amounts don't match the total bill. Please adjust the amounts above.")
                                st.stop()
                        
                        try:
                            # Prepare transaction data
                            transaction_data = {
                                "user_id": DEMO_USER_ID,
                                "date": transaction_date.isoformat(),
                                "amount": amount,
                                "merchant": merchant,
                                "category": category if category else None,
                                "notes": notes if notes else None,
                                "currency": transaction.currency if hasattr(transaction, 'currency') and transaction.currency else "SGD",
                            }
                            
                            # Insert into database
                            tx_response = supabase.table("transactions").insert(transaction_data).execute()
                            
                            # Handle splitting logic with UNEVEN split support
                            if hasattr(transaction, 'is_split') and transaction.is_split:
                                # Use person_friend_mapping from session state (individual dropdowns)
                                person_friend_mapping = st.session_state.get('person_friend_mapping', {})
                                split_display = st.session_state.get('split_display', {})
                                existing_friends_map = st.session_state.get('existing_friends', {})
                                
                                if person_friend_mapping:
                                    # Create debts for each person with their specific amount
                                    for detected_name, friend_name in person_friend_mapping.items():
                                        friend_id = existing_friends_map.get(friend_name)
                                        
                                        # Create friend if not exists (new friend)
                                        if not friend_id:
                                            new_friend = supabase.table("friends").insert({
                                                "user_id": DEMO_USER_ID, 
                                                "name": friend_name
                                            }).execute()
                                            friend_id = new_friend.data[0]['id']
                                        
                                        # Get amount for this person from split_display
                                        friend_amount = split_display.get(detected_name, amount / (len(person_friend_mapping) + 1))
                                        
                                        # Add debt with specific amount
                                        supabase.table("debts").insert({
                                            "user_id": DEMO_USER_ID,
                                            "friend_id": friend_id,
                                            "amount": friend_amount,
                                            "description": f"Split {merchant} bill",
                                            "is_paid": False
                                        }).execute()
                                        st.toast(f"Added debt for {friend_name} (${friend_amount:.2f})")
                            
                            # Get mapping from session state for success message
                            saved_mapping = st.session_state.get('person_friend_mapping', {})
                            st.success(f"✅ Transaction saved!" + (f" Created {len(saved_mapping)} debts." if saved_mapping else ""))
                            
                            # Clear session state
                            del st.session_state['parsed_transaction']
                            if 'is_multi' in st.session_state:
                                del st.session_state['is_multi']
                            if 'final_split_with' in st.session_state:
                                del st.session_state['final_split_with']
                            if 'existing_friends' in st.session_state:
                                del st.session_state['existing_friends']
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error saving transaction: {e}")
                
                if cancel_button:
                    # Clear session state
                    del st.session_state['parsed_transaction']
                    if 'is_multi' in st.session_state:
                        del st.session_state['is_multi']
                    st.rerun()

    elif app_mode == "🤝 Friends & Debts":
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
        
    elif app_mode == "🔎 Search":
        st.header("🔍 Semantic Transaction Search")
        st.markdown("Search your transactions using natural language! Try 'coffee with friends' or 'gym membership'.")
        
        with st.form("search_form"):
            query = st.text_input("Search Query", placeholder="e.g., 'Groceries from last week'")
            
            # Advanced options
            with st.expander("Advanced Options"):
                similarity_threshold = st.slider(
                    "Similarity Threshold", 
                    min_value=0.0, 
                    max_value=1.0, 
                    value=0.5,
                    step=0.05,
                    help="Lower = more results (less strict), Higher = fewer results (more strict)"
                )
                max_results = st.number_input("Max Results", min_value=5, max_value=50, value=20, step=5)
            
            submitted = st.form_submit_button("Search")
            
            if submitted and query:
                with st.spinner("Searching..."):
                    try:
                        # Lazy import to avoid circular dependency issues if any
                        from src.core.embeddings import generate_embedding
                        
                        query_embedding = generate_embedding(query)
                        
                        # Try semantic search first
                        response = supabase.rpc("match_transactions", {
                            "query_embedding": query_embedding,
                            "match_threshold": similarity_threshold,
                            "match_count": max_results,
                            "p_user_id": DEMO_USER_ID
                        }).execute()
                        
                        results = response.data
                        
                        # If no results from semantic search, try keyword fallback
                        search_method = "semantic"
                        if not results:
                            # Fetch all user transactions and do keyword search
                            all_tx = supabase.table("transactions").select("*").eq("user_id", DEMO_USER_ID).execute()
                            
                            if all_tx.data:
                                # Simple keyword matching
                                query_lower = query.lower()
                                keyword_results = []
                                
                                for tx in all_tx.data:
                                    merchant = (tx.get('merchant') or '').lower()
                                    notes = (tx.get('notes') or '').lower()
                                    category = (tx.get('category') or '').lower()
                                    
                                    # Check if any query words appear in transaction fields
                                    if (query_lower in merchant or 
                                        query_lower in notes or 
                                        query_lower in category or
                                        any(word in merchant or word in notes or word in category 
                                            for word in query_lower.split() if len(word) > 2)):
                                        keyword_results.append(tx)
                                
                                results = keyword_results[:max_results]
                                search_method = "keyword"
                        
                        if not results:
                            st.warning("No matching transactions found.")
                            st.info("💡 **Tips:**\n- Try using more general terms (e.g., 'coffee' instead of 'coffee with friends')\n- Check category names: Food & Dining, Shopping, Entertainment, etc.\n- Try merchant names directly")
                        else:
                            # Show success with method used
                            method_label = "🎯 semantic matching" if search_method == "semantic" else "🔍 keyword search"
                            st.success(f"Found {len(results)} transactions using {method_label}")
                            
                            # Display results
                            for i, tx in enumerate(results, 1):
                                with st.container():
                                    col1, col2 = st.columns([3, 1])
                                    
                                    with col1:
                                        st.markdown(f"**{i}. {tx['merchant']}**")
                                        st.caption(f"{tx['category']} • {tx['date']}")
                                        if tx.get('notes'):
                                            st.text(f"💬 {tx['notes']}")
                                    
                                    with col2:
                                        amount = tx['amount']
                                        currency = tx.get('currency', 'SGD')
                                        symbol = get_currency_symbol(currency)
                                        st.markdown(f"### {symbol}{amount:,.2f}")
                                        
                                        # Show similarity score if available
                                        if 'similarity' in tx:
                                            similarity_pct = tx['similarity'] * 100
                                            st.caption(f"Match: {similarity_pct:.0f}%")
                                    
                                    st.divider()
                                    
                    except Exception as e:
                        st.error(f"Search failed: {e}")
                        st.info("💡 **Troubleshooting:**\n- Ensure embeddings are populated (run `python src/data/backfill_embeddings.py`)\n- Verify 'match_transactions' function exists in Supabase\n- Check that transactions have embedding data")

    elif app_mode == "⚙️ Settings":
        st.header("Configuration")
        st.text_input("Ollama Base URL", value=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        st.text_input("Supabase URL", value=os.environ.get("SUPABASE_URL", ""))

if __name__ == "__main__":
    main()
