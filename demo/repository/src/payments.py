from decimal import Decimal


def process_payment(amount: Decimal, currency: str = "USD") -> str:
    if amount <= 0:
        raise ValueError("amount must be positive")
    return f"payment:{currency}:{amount}"

