from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import os
from functools import lru_cache

# Try to import streamlit, but gracefully handle if it's not available
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except (ImportError, RuntimeError):
    STREAMLIT_AVAILABLE = False

from .models import Transaction, TransactionCount, MultiTransactionResponse

# Conditional decorator based on Streamlit availability
def cache_decorator(func):
    """Apply appropriate caching based on context"""
    if STREAMLIT_AVAILABLE:
        try:
            return st.cache_resource(func)
        except:
            # If st.cache_resource fails, fall back to lru_cache
            return lru_cache(maxsize=1)(func)
    else:
        return lru_cache(maxsize=1)(func)

@cache_decorator
def get_llm():
    """Initializes the Ollama Chat Model."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model="llama3.1", base_url=base_url, temperature=0)


@cache_decorator
def get_vision_llm():
    """Initializes the Ollama Vision Model."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    return ChatOllama(model="llama3.2-vision", base_url=base_url, temperature=0)

# Prompt for detecting multiple transactions
MULTI_TRANSACTION_DETECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a transaction analysis assistant. Determine if the input text contains multiple distinct transactions. "
               "Guidelines:\n"
               "- Multiple transactions = separate purchases at different merchants or at different times\n"
               "- Example of multiple: 'Spent 15 at Starbucks and 8.50 at Subway'\n"
               "- Example of single: 'Pizza 40 split with John' (one transaction, split payment)\n"
               "- Example of single: 'Burrito for 12 and chips for 3 at Chipotle' (itemized, but one transaction)\n"
               "Return has_multiple=True only if there are genuinely separate transactions."),
    ("user", "{text}")
])

# Prompt for extracting multiple transactions
MULTI_TRANSACTION_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert financial data extraction assistant. "
               "The input contains MULTIPLE distinct transactions. Extract each transaction separately. "
               "Guidelines:\n"
               "- Each transaction should have its own merchant, amount, and date\n"
               "- Use categories: Food & Dining, Groceries, Transportation, Shopping, Entertainment, Utilities, Healthcare, Other\n"
               "- For dates: use YYYY-MM-DD or relative dates like 'today'\n"
               "- If no date mentioned, use 'today' for all transactions"),
    ("user", "{text}")
])

# Enhanced prompt for single transaction extraction
EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert financial data extraction assistant. "
               "Extract transaction details from the user's text and return them in the specified format. "
               "Guidelines:\n"
               "- Use one of these categories: Food & Dining, Groceries, Transportation, Shopping, Entertainment, Utilities, Healthcare, Other\n"
               "- For splits: set is_split=True and list the names in split_with\n"
               "- For UNEVEN splits, ALWAYS extract individual payment amounts as actual dollar values:\n"
               "  * If user says 'I paid 60, Alice paid 30': set my_share=60.0, split_amounts={{'Alice': 30.0}}\n"
               "  * If user says 'split 70/30 with Mike' on a $100 bill: calculate my_share=70.0, split_amounts={{'Mike': 30.0}}\n"
               "  * If user says 'split 60/40 with Bob' on a $20 bill: calculate my_share=12.0, split_amounts={{'Bob': 8.0}}\n"
               "  * The first number (60, 70) is YOUR percentage, second number (40, 30) is THEIR percentage\n"
               "  * CONVERT percentages to actual dollar amounts using the total bill amount\n"
               "  * If split but no specific amounts/ratios given: leave my_share and split_amounts as null\n"
               "- For dates: use YYYY-MM-DD format, or keep relative dates like 'today' or 'yesterday' as-is\n"
               "- Always provide merchant and amount\n"
               "- If category is unclear, use 'Other'\n"
               "- If no date is mentioned, use 'today'\n"
               "- Amount should be the TOTAL bill amount, not just your share"),
    ("user", "{text}")
])

from langchain_core.messages import HumanMessage
import base64

def extract_receipt_data(image_bytes: bytes) -> Transaction:
    """Extracts transaction data from a receipt image."""
    vision_llm = get_vision_llm()
    
    # Convert image bytes to base64
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Extract the transaction details from this receipt. Return a JSON object with merchant, amount, date, category, and notes."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
    )
    
    # Create structured output chain
    structured_llm = vision_llm.with_structured_output(Transaction)
    
    try:
        return structured_llm.invoke([message])
    except Exception as e:
        print(f"Vision extraction error: {e}")
        return None

