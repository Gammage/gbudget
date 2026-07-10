#!/usr/bin/env python3
import argparse
from datetime import datetime
from config import load_config, save_config, init_config
from database import init_db, add_transaction, get_transactions, update_transaction, delete_transaction, mark_cleared, add_recurring, get_recurring, delete_recurring, transaction_exists_in_month, get_connection
from exporters import export_statement


def main():
    config = load_config()
    check_statement_prompt(config)

    parser = argparse.ArgumentParser(description="gbudget — Personal CLI Budget")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser("init", help="First-time setup")
    init_parser.add_argument("--vault", required=True)

    # config
    config_parser = subparsers.add_parser("config", help="View or update settings")
    config_parser.add_argument("--vault")

    # add
    add_parser = subparsers.add_parser("add", help="Add a transaction")
    add_parser.add_argument("amount", type=float)
    add_parser.add_argument("description", type=str)
    add_parser.add_argument("-c", "--category", default="General")
    add_parser.add_argument("-d", "--date", default=datetime.today().strftime("%Y-%m-%d"))
    add_parser.add_argument("--pending", action="store_true", help="Mark as pending (not yet cleared by bank)")

    # list
    list_parser = subparsers.add_parser("list", help="List transactions")
    list_parser.add_argument("--month")
    list_parser.add_argument("-c", "--category")
    list_parser.add_argument("--status", choices=["pending", "cleared"])

    # summary
    summary_parser = subparsers.add_parser("summary", help="Income/expense summary")
    summary_parser.add_argument("--month")
    summary_parser.add_argument("--by-category", action="store_true")

    # edit
    edit_parser = subparsers.add_parser("edit", help="Edit a transaction")
    edit_parser.add_argument("id", type=int)
    edit_parser.add_argument("-a", "--amount", type=float)
    edit_parser.add_argument("-d", "--description")
    edit_parser.add_argument("-c", "--category")
    edit_parser.add_argument("--type", choices=["income", "expense"], dest="type_")
    edit_parser.add_argument("--status", choices=["pending", "cleared"])

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a transaction")
    delete_parser.add_argument("id", type=int)

    # clear
    clear_parser = subparsers.add_parser("clear", help="Mark transactions as cleared")
    clear_parser.add_argument("ids", type=int, nargs="+", metavar="ID")

    # export
    export_parser = subparsers.add_parser("export", help="Generate monthly statement")
    export_parser.add_argument("--month")

    # recurring
    recurring_parser = subparsers.add_parser("recurring", help="Manage recurring transactions")
    recurring_sub = recurring_parser.add_subparsers(dest="recurring_cmd", required=True)

    recurring_add = recurring_sub.add_parser("add", help="Create a recurring template")
    recurring_add.add_argument("amount", type=float)
    recurring_add.add_argument("description", type=str)
    recurring_add.add_argument("-c", "--category", default="General")
    recurring_add.add_argument("-d", "--day", type=int, required=True)
    recurring_add.add_argument("--income", action="store_true")

    recurring_list = recurring_sub.add_parser("list", help="Show all recurring templates")

    recurring_del = recurring_sub.add_parser("delete", help="Delete a recurring template")
    recurring_del.add_argument("id", type=int)

    args = parser.parse_args()

    if args.command == "init":
        init_config(args.vault)
        init_db()
        print(f"gbudget initialised. Vault: {args.vault}")

    elif args.command == "config":
        if args.vault:
            config["vault_path"] = args.vault
            save_config(config)
            print(f"Vault path updated to: {args.vault}")
        else:
            print("Current settings:")
            for key, value in config.items():
                print(f"  {key}: {value}")

    elif args.command == "add":
        type_ = "expense" if args.amount < 0 else "income"
        status = "pending" if args.pending else "cleared"
        tid = add_transaction(abs(args.amount), args.description, args.category, args.date, type_, status)
        auto_export(config, args.date[:7])
        print(f"Transaction #{tid} added.")

    elif args.command == "list":
        txns = get_transactions(month=args.month, category=args.category, status=args.status)
        if not txns:
            print("No transactions found.")
            return
        print(f"{'ID':>3}  {'Date':<10}  {'Type':<7}  {'Amount':>8}  {'Category':<12}  {'Status':<8}  Description")
        print("-" * 80)
        for t in txns:
            sign = "+" if t.type == "income" else "-"
            print(f"{t.id:>3}  {t.date:<10}  {t.type:<7}  {sign}£{t.amount:>6.2f}  {t.category:<12}  {t.status:<8}  {t.description}")

    elif args.command == "summary":
        txns = get_transactions(month=args.month)
        if not txns:
            print("No transactions found.")
            return
        total_income = sum(t.amount for t in txns if t.type == "income")
        total_expenses = sum(t.amount for t in txns if t.type == "expense")
        net = total_income - total_expenses
        month_label = args.month or "all time"
        print(f"\nSummary for {month_label}")
        print(f"{'Income:':<20} £{total_income:>8.2f}")
        print(f"{'Expenses:':<20} £{total_expenses:>8.2f}")
        print(f"{'Net:':<20} £{net:>8.2f}")
        if args.by_category:
            categories = {}
            for t in txns:
                if t.type == "expense":
                    categories[t.category] = categories.get(t.category, 0) + t.amount
            if categories:
                print(f"\n{'Category':<15} {'Spent':>10}")
                print("-" * 27)
                for cat, total in sorted(categories.items(), key=lambda x: -x[1]):
                    pct = (total / total_expenses * 100) if total_expenses else 0
                    print(f"{cat:<15} £{total:>8.2f}  ({pct:.0f}%)")

    elif args.command == "edit":
        kwargs = {}
        if args.amount is not None:
            kwargs["amount"] = abs(args.amount)
            if args.amount < 0:
                kwargs["type"] = "expense"
            else:
                kwargs["type"] = "income"
        if args.description is not None:
            kwargs["description"] = args.description
        if args.category is not None:
            kwargs["category"] = args.category
        if args.type_ is not None:
            kwargs["type"] = args.type_
        if args.status is not None:
            kwargs["status"] = args.status
        if not kwargs:
            print("Nothing to edit.")
            return
        update_transaction(args.id, **kwargs)
        auto_export(config)
        print(f"Transaction #{args.id} updated.")

    elif args.command == "delete":
        delete_transaction(args.id)
        auto_export(config)
        print(f"Transaction #{args.id} deleted.")

    elif args.command == "clear":
        mark_cleared(args.ids)
        auto_export(config)
        print(f"Transactions marked as cleared: {args.ids}")

    elif args.command == "export":
        month = args.month or datetime.today().strftime("%Y-%m")
        path = export_statement(config, month)
        print(f"Statement written to {path}")

    elif args.command == "recurring":
        if args.recurring_cmd == "add":
            type_ = "income" if args.income else "expense"
            rid = add_recurring(abs(args.amount), args.description, args.category, type_, args.day)
            print(f"Recurring #{rid} created.")
        elif args.recurring_cmd == "list":
            items = get_recurring()
            if not items:
                print("No recurring templates.")
            else:
                print(f"{'ID':>2}  {'Amount':>8}  {'Description':<15}  {'Category':<12}  {'Type':<7}  {'Day':>3}  Last Gen")
                print("-" * 75)
                total = 0
                for r in items:
                    sign = "+" if r["type"] == "income" else "-"
                    last_gen = r["last_generated"] or "—"
                    print(f"{r['id']:>2}  {sign}£{r['amount']:>6.2f}  {r['description']:<15}  {r['category']:<12}  {r['type']:<7}  {r['day']:>3}  {last_gen}")
                    if r["type"] == "expense":
                        total += r["amount"]
                print("-" * 75)
                print(f"{'Total monthly outgoings:':<50} £{total:>8.2f}")
        elif args.recurring_cmd == "delete":
            delete_recurring(args.id)
            print(f"Recurring #{args.id} deleted.")


def auto_export(config, month=None):
    if not config.get("vault_path"):
        return
    if month is None:
        month = datetime.today().strftime("%Y-%m")
    export_statement(config, month)


def check_statement_prompt(config):
    vault = config.get("vault_path", "")
    if not vault:
        return
    today = datetime.today()
    current_month = today.strftime("%Y-%m")
    if current_month != config.get("last_statement_month", ""):
        last_month = today.replace(day=1)
        if last_month.month == 1:
            last_month = last_month.replace(year=last_month.year - 1, month=12)
        else:
            last_month = last_month.replace(month=last_month.month - 1)
        label = last_month.strftime("%B %Y")
        try:
            response = input(f"Generate statement for {label}? [y/N] ").strip().lower()
        except EOFError:
            response = "n"
        if response == "y":
            month = last_month.strftime("%Y-%m")
            export_statement(config, month)
            print(f"Statement for {label} generated.")
        config["last_statement_month"] = current_month
        save_config(config)

        # recurring auto-generation prompt
        items = get_recurring()
        due = [r for r in items if r.get("last_generated") != current_month]
        if due:
            try:
                response = input(f"Generate recurring transactions for {today.strftime('%B %Y')}? [y/N] ").strip().lower()
            except EOFError:
                response = "n"
            if response == "y":
                count = 0
                for r in due:
                    if transaction_exists_in_month(r["amount"], r["description"], current_month):
                        continue
                    date_str = f"{current_month}-{r['day']:02d}"
                    add_transaction(r["amount"], r["description"], r["category"], date_str, r["type"], "pending")
                    conn = get_connection()
                    conn.execute("UPDATE recurring SET last_generated = ? WHERE id = ?", (current_month, r["id"]))
                    conn.commit()
                    conn.close()
                    count += 1
                if count:
                    print(f"{count} recurring transaction(s) generated.")
                    auto_export(config, current_month)
                else:
                    print("All recurring items already exist for this month.")


if __name__ == "__main__":
    main()
