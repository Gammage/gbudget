import os
from datetime import datetime, timedelta
from database import get_connection


def export_statement(config, month):
    vault = os.path.expanduser(config["vault_path"])
    output_dir = os.path.join(vault, "files", "money")
    os.makedirs(output_dir, exist_ok=True)

    year_str, month_str = month.split("-")
    year = int(year_str)
    month_num = int(month_str)

    first_day = datetime(year, month_num, 1)
    if month_num == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month_num + 1, 1) - timedelta(days=1)
    last_day_label = last_day.strftime("%b %d, %Y").replace(" 0", " ")

    month_label = first_day.strftime("%B %Y")
    period_label = f"{first_day.strftime('%b')} {first_day.day} – {last_day_label}"

    conn = get_connection()

    # opening balance: sum of all transactions before this month
    row = conn.execute(
        "SELECT SUM(CASE WHEN type = 'income' THEN amount ELSE -amount END) FROM transactions WHERE date < ? AND status = 'cleared'",
        (month_str + "-01",)
    ).fetchone()
    opening_balance = row[0] or 0.0

    # this month's transactions
    rows = conn.execute(
        "SELECT * FROM transactions WHERE strftime('%Y-%m', date) = ? ORDER BY date, id",
        (month,)
    ).fetchall()
    txns = [dict(r) for r in rows]

    cleared_txns = [t for t in txns if t["status"] == "cleared"]
    pending_txns = [t for t in txns if t["status"] == "pending"]

    total_income = sum(t["amount"] for t in txns if t["type"] == "income")
    total_expenses = sum(t["amount"] for t in txns if t["type"] == "expense")
    net_change = total_income - total_expenses
    closing_balance = opening_balance + net_change

    today_str = datetime.today().strftime("%b %d, %Y").replace(" 0", " ")

    lines = []
    lines.append("---")
    lines.append(f'id: {month}-statement')
    lines.append("aliases: []")
    lines.append("tags:")
    lines.append("  - money")
    lines.append("  - budget")
    lines.append("  - statement")
    lines.append("---")
    lines.append("")
    lines.append(f"# Monthly Statement — {month_label}")
    lines.append("")
    lines.append(f"**Period:** {period_label}")
    lines.append(f"**Generated:** {today_str}")
    lines.append("")
    lines.append("## Account Overview")
    lines.append("")
    lines.append("| | Amount |")
    lines.append("|---|---|")
    lines.append(f"| Opening Balance | £{opening_balance:.2f} |")
    lines.append(f"| Income | £{total_income:.2f} |")
    lines.append(f"| Expenses | -£{total_expenses:.2f} |")
    lines.append(f"| **Net Change** | **{'£' + f'{net_change:.2f}' if net_change >= 0 else '-£' + f'{abs(net_change):.2f}'}** |")
    lines.append(f"| **Closing Balance** | **£{closing_balance:.2f}** |")
    lines.append(f"| **Saved this month** | **£{net_change:.2f}** |")
    lines.append("")

    if cleared_txns:
        lines.append("## Transactions (Cleared)")
        lines.append("")
        lines.append("| Date | Description | Category | Amount |")
        lines.append("|---|---|---|---|")
        for t in cleared_txns:
            d = datetime.strptime(t["date"], "%Y-%m-%d")
            date_label = d.strftime("%b %-d")
            sign = "+" if t["type"] == "income" else "-"
            lines.append(f"| {date_label} | {t['description']} | {t['category']} | {sign}£{t['amount']:.2f} |")
        lines.append("")

    # expenses by category
    categories = {}
    for t in cleared_txns:
        if t["type"] == "expense":
            categories[t["category"]] = categories.get(t["category"], 0) + t["amount"]

    if categories:
        lines.append("## Expenses by Category")
        lines.append("")
        lines.append("| Category | Spent | % of Total |")
        lines.append("|---|---|---|")
        for cat, total in sorted(categories.items(), key=lambda x: -x[1]):
            pct = (total / total_expenses * 100) if total_expenses else 0
            lines.append(f"| {cat} | £{total:.2f} | {pct:.0f}% |")
        lines.append("")

    if pending_txns:
        lines.append("## Pending Transactions")
        lines.append("")
        lines.append("| Date | Description | Category | Amount |")
        lines.append("|---|---|---|---|")
        for t in pending_txns:
            d = datetime.strptime(t["date"], "%Y-%m-%d")
            date_label = d.strftime("%b %-d")
            sign = "+" if t["type"] == "income" else "-"
            lines.append(f"| {date_label} | {t['description']} | {t['category']} | {sign}£{t['amount']:.2f} |")
        lines.append("")

    conn.close()

    content = "\n".join(lines)
    filename = f"{month}-statement.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(content)

    return filepath
