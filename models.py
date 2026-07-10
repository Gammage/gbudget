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
