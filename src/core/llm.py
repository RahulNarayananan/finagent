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
               "- If no date mentioned, use 'today' for all transactions\n"
               "\n"
               "IMPORTANT - Notes Field with Line Items:\n"
               "- Include specific items purchased in the 'notes' field as a comma-separated list\n"
               "- Examples: 'coffee, croissant' or 'milk, eggs, bread' or 'lunch with friends, pizza'\n"
               "- This helps with future semantic searches (e.g., searching for 'coffee' or 'pizza')\n"
               "- Include relevant context like 'with friends', 'for work', location details, etc."),
    ("user", "{text}")
])

# Enhanced prompt for single transaction extraction
EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an expert financial data extraction assistant. "
               "Extract transaction details from the user's text and return them in the specified format. "
               "Guidelines:\n"
               "- Use one of these categories: Food & Dining, Groceries, Transportation, Shopping, Entertainment, Utilities, Healthcare, Other\n"
               "\n"
               "CRITICAL - Amount Extraction Rules:\n"
               "- The 'amount' field MUST be the TOTAL bill amount mentioned by the user\n"
               "- Look for keywords: 'spent', 'paid', 'cost', 'bill', or standalone numbers with $ or currency words\n"
               "- Extract the EXACT amount mentioned, do NOT modify or calculate\n"
               "- Examples of CORRECT amount extraction:\n"
               "  * 'Uber 50 bucks' → amount: 50.0 (NOT 100.0)\n"
               "  * 'Spent 20 at GYG' → amount: 20.0 (NOT 10.0)\n"
               "  * 'Breakfast $15.50' → amount: 15.50\n"
               "  * 'Paid $100 for dinner' → amount: 100.0\n"
               "  * 'Bill was 80 dollars' → amount: 80.0\n"
               "- If user mentions 'I paid X and Bob paid Y', the amount is X + Y (total bill)\n"
               "- NEVER halve or double the amount unless explicitly stated\n"
               "\n"
               "IMPORTANT - Notes Field with Line Items:\n"
               "- In the 'notes' field, include a detailed list of items purchased if mentioned\n"
               "- Format line items as a comma-separated list for easy searching\n"
               "- Examples:\n"
               "  * 'Bought coffee and croissant at Starbucks' → notes: 'coffee, croissant'\n"
               "  * 'Groceries: milk, eggs, bread, cheese' → notes: 'milk, eggs, bread, cheese'\n"
               "  * 'Lunch with friends, had pizza and drinks' → notes: 'lunch with friends, pizza, drinks'\n"
               "  * 'Gas for car' → notes: 'gas, fuel'\n"
               "- Include any relevant context (who, what, where) that helps with future searches\n"
               "- Keep it concise but descriptive\n"
               "\n"
               "Split Payment Rules:\n"
               "- For splits: set is_split=True and list the names in split_with\n"
               "- For UNEVEN splits, ALWAYS extract individual payment amounts as actual dollar values:\n"
               "  * If user says 'I paid 60, Alice paid 30': amount=90, my_share=60.0, split_amounts={{'Alice': 30.0}}\n"
               "  * If user says 'split 70/30 with Mike' on a $100 bill: amount=100, my_share=70.0, split_amounts={{'Mike': 30.0}}\n"
               "  * If user says 'split 60/40 with Bob' on a $20 bill: amount=20, my_share=12.0, split_amounts={{'Bob': 8.0}}\n"
               "  * If user says 'Uber 50 bucks split 60/40 with Sarah': amount=50, my_share=30.0, split_amounts={{'Sarah': 20.0}}\n"
               "  * The first number (60, 70) is YOUR percentage, second number (40, 30) is THEIR percentage\n"
               "  * CONVERT percentages to actual dollar amounts using the TOTAL bill amount (from amount field)\n"
               "  * If split but no specific amounts/ratios given: leave my_share and split_amounts as null\n"
               "\n"
               "Other Rules:\n"
               "- For dates: use YYYY-MM-DD format, or keep relative dates like 'today' or 'yesterday' as-is\n"
               "- Always provide merchant and amount\n"
               "- If category is unclear, use 'Other'\n"
               "- If no date is mentioned, use 'today'"),
    ("user", "{text}")
])

from langchain_core.messages import HumanMessage
import base64

def extract_receipt_data(image_bytes: bytes, context: str = None) -> Transaction:
    """Extracts transaction data from a receipt image."""
    vision_llm = get_vision_llm()
    
    # Convert image bytes to base64
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Build prompt - explicit about split detection
    prompt_text = """Extract transaction data from this receipt image for bill splitting.

STEP 1 - Extract Basic Info:
- merchant: Name of the business/store
- amount: Total amount (including all taxes)
- date: Transaction date (YYYY-MM-DD format)
- category: Type of purchase (Food/Transport/Shopping/Fuel/Entertainment/etc)
- currency: CRITICAL - Auto-detect from symbol on receipt:
  * ₹ = INR (Indian Rupees)
  * $ = Check context - could be USD, SGD, AUD
  * S$ or SGD = SGD (Singapore Dollars)
  * € = EUR (Euro)
  * £ = GBP (British Pound)
  * ¥ = JPY or CNY (Japanese Yen / Chinese Yuan)
  Set to 3-letter code (INR, USD, SGD, EUR, GBP, JPY, etc.)

Examples:
  - "GST(9%) $2.57" → gst: 2.57
  - "CGST 2.5% + SGST 2.5%" → gst: sum of both
  - "Service Tax 18%" → gst: tax amount

STEP 3 - Extract Line Items (for bill splitting):
If the receipt has itemized purchases (restaurants, grocery stores):
- Extract each item name and its price
- IGNORE tax lines (those go in gst field)
- Focus on actual products/dishes purchased

For simple receipts (e.g., petrol, parking):
- May only have 1 item, that's fine

STEP 4 - Match Items to People (IF context provided):
If user provides context mentioning multiple people:

1. Set is_split = true
2. Extract person names (exclude "I", "me") → split_with: ["Alice", "Bob"]
3. Match each person to their items mentioned in context
4. Look up item prices from Step 3
5. Create split_amounts: {"Alice": price, "Bob": price}

IMPORTANT:
- split_amounts only contains OTHER people, NOT the user
- Use ACTUAL prices from receipt, not equal splits
- Match item names flexibly (e.g., "latte" matches "Iced Latte 200ml")
- If items not clearly itemized (e.g., petrol receipt), leave split_amounts empty

EXAMPLES:

Example 1 - Restaurant (itemized):
Receipt: Coffee $5.50, Latte $4.80, Total $10.30
Context: "alice had latte"
Output: is_split=true, split_with=["Alice"], split_amounts={"Alice": 4.80}

Example 2 - Grocery Store (many items):
Receipt: 25 items, Total ₹5025
Context: "split equally with bob"
Output: is_split=true, split_with=["Bob"], split_amounts={} (too many items, use equal split)

Example 3 - Petrol (simple):
Receipt: Petrol 45.30L @ ₹101.56, Total ₹4600
Context: "shared with alice"
Output: is_split=true, split_with=["Alice"], split_amounts={} (single item, use equal split)

CRITICAL RULES:
- Work with ANY currency (₹, $, €, £, etc.)
- Work with ANY receipt format (restaurant, store, fuel, etc.)
- Only populate split_amounts if items are clearly itemized AND context specifies who ordered what
- When in doubt, leave split_amounts empty (system will do equal split)
"""
    
    if context:
        prompt_text += f"""

USER CONTEXT:
{context}

IF this context mentions multiple people:
1. Set is_split = true
2. Extract person names → split_with
3. If items are itemized AND context specifies who ordered what → populate split_amounts
4. Otherwise leave split_amounts empty for equal split
"""
    else:
        prompt_text += "\n\n(No context provided. Extract basic info only, set is_split=false)"

    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
    )
    
    # Create structured output chain
    structured_llm = vision_llm.with_structured_output(Transaction)
    
    try:
        transaction = structured_llm.invoke([message])
        
        # Debug output
        print(f"\n{'='*50}")
        print(f"[DEBUG] LLM Response:")
        print(f"  is_split: {transaction.is_split}")
        print(f"  split_with: {transaction.split_with}")
        print(f"  split_amounts: {transaction.split_amounts}")
        print(f"  gst: {transaction.gst}")
        print(f"  amount: {transaction.amount}")
        print(f"{'='*50}\n")
        
        # Post-processing: If LLM failed to detect split but context clearly indicates it
        if transaction and context and not transaction.is_split:
            print(f"[DEBUG] Post-processing: LLM didn't set is_split, checking context...")
            print(f"[DEBUG] Context: {context[:100]}...")
            
            # Check for split indicators in context
            context_lower = context.lower()
            
            # Only check for explicit split keywords (not "had" - too generic)
            explicit_split_keywords = ['split', 'shared', 'divide']
            has_explicit_split = any(word in context_lower for word in explicit_split_keywords)
            print(f"[DEBUG] Has explicit split keyword: {has_explicit_split}")
            
            # Find names by looking for words that appear with ordering keywords
            # This works even if names are lowercase (e.g., "alice had" or "bob ordered")
            ordering_keywords = ['ordered', 'had', 'got', 'wants', 'paid']
            person_names = []
            
            # Common words to exclude
            exclude_words = {'i', 'me', 'my', 'he', 'she', 'they', 'we', 'the', 'a', 'and', 'or', 'other', 
                           'drinks', 'were', 'by', 'with', 'for', 'at', 'was', 'is', 'it', 'this', 'that'}
            
            # Look for patterns: <name> <ordering_keyword> OR <ordering_keyword> by <name>
            words = context_lower.split()
            for i, word in enumerate(words):
                word_clean = word.strip(',.!?;:')
                
                # Pattern 1: "alice had" - word before ordering keyword
                if word_clean in ordering_keywords and i > 0:
                    prev_word = words[i-1].strip(',.!?;:')
                    if prev_word not in exclude_words and len(prev_word) > 1:
                        name = prev_word.capitalize()
                        if name.lower() not in [n.lower() for n in person_names]:
                            person_names.append(name)
                            print(f"[DEBUG] Detected person: {name} (before '{word_clean}')")
                
                # Pattern 2: "ordered by alice" - word after 'by' following an ordering keyword
                if word_clean == 'by' and i > 0 and i < len(words) - 1:
                    prev_word = words[i-1].strip(',.!?;:')
                    next_word = words[i+1].strip(',.!?;:')
                    # Check if previous word was an ordering keyword
                    if prev_word in ordering_keywords or prev_word == 'were':
                        if next_word not in exclude_words and len(next_word) > 1:
                            name = next_word.capitalize()
                            if name.lower() not in [n.lower() for n in person_names]:
                                person_names.append(name)
                                print(f"[DEBUG] Detected person: {name} (after 'by')")

            
            print(f"[DEBUG] Final person names: {person_names} (count: {len(person_names)})")
            
            # Only mark as split if:
            # 1. Explicit split keyword found, OR
            # 2. Multiple different people (2+) are mentioned with ordering context
            if has_explicit_split or len(person_names) >= 2:
                transaction.is_split = True
                transaction.split_with = person_names if person_names else []
                print(f"[DEBUG] ✅ AUTO-DETECTED SPLIT with: {person_names if person_names else 'explicit split keyword'}")
            else:
                print(f"[DEBUG] ❌ Not marking as split (explicit={has_explicit_split}, people_count={len(person_names)})")
        elif transaction and transaction.is_split:
            print(f"[DEBUG] LLM correctly set is_split=true, split_with={transaction.split_with}")
        
        return transaction
    except Exception as e:
        print(f"Vision extraction error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_financial_recommendations(
    user_spending: dict,
    population_avg: dict,
    overspending: list,
    underspending: list,
    currency_symbol: str = "$"
) -> str:
    """
    Generate personalized financial recommendations using LLM.
    
    Args:
        user_spending: User's spending by category {category: amount}
        population_avg: Population averages {category: amount}
        overspending: List of (category, pct_diff, dollar_diff) for overspending
        underspending: List of (category, pct_diff, dollar_diff) for underspending
        currency_symbol: Currency symbol to use in output
    
    Returns:
        Markdown-formatted recommendations string
    """
    llm = get_llm()
    
    # Prepare data for the prompt
    overspending_summary = []
    for category, pct_diff, dollar_diff in overspending:
        user_amt = user_spending.get(category, 0)
        pop_amt = population_avg.get(category, 0)
        overspending_summary.append({
            "category": category,
            "user_amount": user_amt,
            "population_avg": pop_amt,
            "percentage_over": pct_diff,
            "dollar_over": dollar_diff
        })
    
    underspending_summary = []
    for category, pct_diff, dollar_diff in underspending:
        user_amt = user_spending.get(category, 0)
        pop_amt = population_avg.get(category, 0)
        underspending_summary.append({
            "category": category,
            "user_amount": user_amt,
            "population_avg": pop_amt,
            "percentage_under": abs(pct_diff),
            "dollar_under": abs(dollar_diff)
        })
    
    # Build clear, structured data strings
    overspending_text = ""
    if overspending_summary:
        for item in overspending_summary:
            overspending_text += f"\n{item['category']}:\n"
            overspending_text += f"  - You spent: {currency_symbol}{item['user_amount']:,.2f}\n"
            overspending_text += f"  - Average user: {currency_symbol}{item['population_avg']:,.2f}\n"
            overspending_text += f"  - Difference: {currency_symbol}{item['dollar_over']:,.2f} MORE ({item['percentage_over']:.1f}% over average)\n"
    else:
        overspending_text = "\nNone - You're doing great!"
    
    underspending_text = ""
    if underspending_summary:
        for item in underspending_summary:
            underspending_text += f"\n{item['category']}:\n"
            underspending_text += f"  - You spent: {currency_symbol}{item['user_amount']:,.2f}\n"
            underspending_text += f"  - Average user: {currency_symbol}{item['population_avg']:,.2f}\n"
            underspending_text += f"  - Savings: {currency_symbol}{item['dollar_under']:,.2f} LESS ({item['percentage_under']:.1f}% below average)\n"
    else:
        underspending_text = "\nNone"
    
    # Calculate summary stats
    total_categories = len(overspending_summary) + len(underspending_summary)
    total_savings_potential = sum(item['dollar_over'] for item in overspending_summary)
    
    # Create simple text lists
    overspend_list = []
    for item in overspending_summary:
        overspend_list.append(f"{item['category']}: You spent {currency_symbol}{item['user_amount']:,.2f}, average is {currency_symbol}{item['population_avg']:,.2f} (that's {item['percentage_over']:.0f}% more)")
    
    underspend_list = []
    for item in underspending_summary:
        underspend_list.append(f"{item['category']}: You spent {currency_symbol}{item['user_amount']:,.2f}, average is {currency_symbol}{item['population_avg']:,.2f} (that's {item['percentage_under']:.0f}% less)")
    
    prompt = f"""You are a helpful friend giving financial advice. Be warm, encouraging, and specific.

THE DATA:

Where you're spending MORE than others:
{chr(10).join(overspend_list) if overspend_list else "None - you're doing great!"}

Where you're spending LESS than others:
{chr(10).join(underspend_list) if underspend_list else "None"}

YOUR JOB:
Write a friendly 150-word analysis with:

1. A warm 2-sentence summary (like: "Hey! I looked at your spending. You're doing well in some areas, but there's room to save in a couple categories.")

2. For each category above, write ONE paragraph with:
   - Category name in bold: **Category Name**
   - What the numbers show
   - One specific tip to improve
   - Add a blank line between each category

CRITICAL RULES:
- Use normal sentences with proper spacing
- NO emoji
- NO arrows or special symbols
- Write like you're texting a friend
- Include actual dollar amounts from the data
- Keep it under 150 words total

EXAMPLE OUTPUT:

**Summary**

You're managing your budget pretty well overall. I noticed you're spending a bit more than average in healthcare, but you're crushing it with groceries and utilities.

**Healthcare**

You spent $300 while most people spend around $160. That's about 88% more than average. Have you looked into negotiating your rates or checking if there are better insurance options? You could potentially save around $140 per month.

**Groceries**

Nice work here! You spent $96 compared to the average of $890. You're clearly being smart about grocery shopping. Keep it up!

Now write the analysis:"""

    try:
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return "Unable to generate recommendations at this time. Please try again later."


