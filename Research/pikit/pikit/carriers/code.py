def calculate_total(items):
    """Return the sum of item prices, applying a 10% discount over $100."""
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    if total > 100:
        total *= 0.9
    return round(total, 2)
