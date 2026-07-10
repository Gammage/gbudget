import os
from datetime import datetime, timedelta
from database import get_connection, get_debts, get_debt_payments, calculate_debt_balance


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
    cleared_income = sum(t["amount"] for t in cleared_txns if t["type"] == "income")
    cleared_expenses = sum(t["amount"] for t in cleared_txns if t["type"] == "expense")
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

    # recurring templates
    recurring_rows = conn.execute("SELECT * FROM recurring ORDER BY day").fetchall()
    if recurring_rows:
        lines.append("## Recurring Payments")
        lines.append("")
        lines.append("| Description | Category | Amount | Due Day |")
        lines.append("|---|---|---|---|")
        recurring_total = 0
        for r in recurring_rows:
            sign = "+" if r["type"] == "income" else "-"
            amt = r["amount"]
            lines.append(f"| {r['description']} | {r['category']} | {sign}£{amt:.2f} | {r['day']} |")
            if r["type"] == "expense":
                recurring_total += amt
        lines.append("")
        lines.append(f"**Total outgoings:** -£{recurring_total:.2f}")
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
        cleared_net = cleared_income - cleared_expenses
        lines.append("")
        lines.append(f"**Total:** {'£' + f'{cleared_net:.2f}' if cleared_net >= 0 else '-£' + f'{abs(cleared_net):.2f}'}")
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

    # Debts & Loans section
    debts = get_debts(status="active")
    if debts:
        lines.append("## Debts & Loans")
        lines.append("")
        lines.append("| Debt | Balance | Interest | Payments | New Balance |")
        lines.append("|---|---|---|---|---|")
        total_debt = 0
        for d in debts:
            balance = calculate_debt_balance(d)
            # Calculate interest accrued this month
            start = datetime.strptime(d.start_date, "%Y-%m-%d")
            month_dt = datetime.strptime(month + "-01", "%Y-%m-%d")
            months_elapsed = (month_dt.year - start.year) * 12 + (month_dt.month - start.month)
            monthly_rate = d.annual_rate / 12 / 100
            if months_elapsed > 0:
                interest_this_month = d.initial_amount * monthly_rate
            else:
                interest_this_month = 0
            # Get payments this month
            payments = get_debt_payments(debt_id=d.id, month=month)
            payments_total = sum(p["amount"] for p in payments)
            new_balance = balance - payments_total + interest_this_month
            new_balance = max(new_balance, 0.0)
            total_debt += new_balance
            lines.append(f"| {d.name} | £{balance:.2f} | +£{interest_this_month:.2f} | -£{payments_total:.2f} | £{new_balance:.2f} |")
        lines.append("")
        lines.append(f"**Total debt:** £{total_debt:.2f}")
        lines.append("")

    conn.close()

    content = "\n".join(lines) + "\n"
    filename = f"{month}-statement.md"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        f.write(content)

    return filepath
