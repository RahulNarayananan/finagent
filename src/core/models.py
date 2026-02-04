from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date

class Transaction(BaseModel):
    """Represents a single financial transaction parsed from text or receipt."""
    merchant: str = Field(description="Name of the merchant or business")
    amount: float = Field(description="Total transaction amount")
    date: str = Field(description="Date of the transaction (YYYY-MM-DD or relative like 'today')")
    category: Optional[str] = Field(default=None, description="Category of the expense (e.g. Food, Transport, Utilities)")
    notes: Optional[str] = Field(default=None, description="Additional notes or context about the purchase")
    is_split: bool = Field(default=False, description="True if this bill should be split with others")
    split_with: Optional[List[str]] = Field(default=None, description="List of names of people to split the bill with")
    
    # Enhanced split tracking
    my_share: Optional[float] = Field(default=None, description="Amount the user paid (for uneven splits)")
    split_amounts: Optional[Dict[str, float]] = Field(default=None, description="Individual split amounts per person (e.g., {'Alice': 30.0, 'Bob': 20.0})")
    
    # Tax handling
    gst: Optional[float] = Field(default=None, description="GST/tax amount to be split equally among all people")
    
    # Currency support
    currency: Optional[str] = Field(default="SGD", description="Currency code (USD, EUR, SGD, INR, etc.)")

class TransactionCount(BaseModel):
    """Response for detecting multiple transactions."""
    has_multiple: bool = Field(description="True if input contains multiple distinct transactions")
    count: int = Field(description="Number of transactions detected")
    reason: Optional[str] = Field(default=None, description="Brief explanation of why multiple transactions were detected")

class MultiTransactionResponse(BaseModel):
    """Container for multiple transactions extracted from a single input."""
    transactions: List[Transaction] = Field(description="List of extracted transactions")
    count: int = Field(description="Number of transactions extracted")

class LineItem(BaseModel):
    """Represents a single line item on a receipt."""
    description: str = Field(description="Name or description of the item")
    quantity: int = Field(default=1, description="Quantity purchased")
    price: float = Field(description="Price per unit or total price for this line")

class Receipt(BaseModel):
    """Represents a full receipt with multiple items."""
    merchant: str
    date: str
    total_amount: float
    items: List[LineItem]
