from dataclasses import dataclass
from datetime import date

@dataclass
class Transaction:
    id: int | None = None
    amount: float = 0.0
    description: str = ""
    category: str = "General"
    date: str = "" # YYYY-MM-DD
    type: str = "expense" # "income" or "expense"
    status: str = "pending" # "pending" or "cleared"
    created_at: str = ""

@dataclass
class Debt:
    id: int | None = None
    name: str = ""
    initial_amount: float = 0.0
    annual_rate: float = 0.0
    start_date: str = "" # YYYY-MM-DD
    status: str = "active" # "active" or "paid_off"
    created_at: str = ""
