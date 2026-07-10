# gbudget — Personal CLI Budget App

Track income and expenses from the terminal. Generates monthly markdown statements in your Obsidian vault.

## Install

Choose the method that works for your system:

### Any system (no install)
```bash
git clone <repo>
cd gbudget
./gbudget --help        # Linux/Mac/WSL
gbudget.bat --help      # Windows (cmd)
```

### Linux/Mac — global command (pip)
```bash
pip install -e .
gbudget --help
```

### Windows — add to PATH
Add the cloned folder to your PATH, then `gbudget.bat` works anywhere.

## Data storage

| System | Database location | Config location |
|---|---|---|
| Linux/Mac | `~/.local/share/gbudget/budget.db` | `~/.config/gbudget/config.json` |
| Windows | `%APPDATA%/gbudget/budget.db` | `%APPDATA%/gbudget/config.json` |

## Usage

```
gbudget init --vault ~/notes
gbudget add 2000 "salary" -d 2026-07-01
gbudget add -50 "groceries" -c Food -d 2026-07-03
gbudget add -50 "groceries" -c Food -d 2026-07-03 --pending
gbudget list --month 2026-07
gbudget summary --month 2026-07 --by-category
gbudget edit 1 -c Household
gbudget clear 1 2
gbudget delete 3
gbudget export --month 2026-07
gbudget config
gbudget config --vault ~/Documents/Notes
gbudget recurring add 12 "Netflix" -c Subscriptions -d 15
gbudget recurring add 500 "Rent" -c Housing -d 1
gbudget recurring list
gbudget recurring delete 1
```

## Commands

**`init --vault PATH`**
  First-time setup. Creates config, database, and vault folder.
  Example: `gbudget init --vault ~/notes`

**`add AMOUNT DESC [-c CAT] [-d DATE] [--pending]`**
  Add a transaction. Negative amount = expense, positive = income.
  Defaults to **cleared**. Use `--pending` for unconfirmed items.
  Examples:
  `gbudget add 2000 "salary"` — income, cleared
  `gbudget add -50 "groceries" -c Food` — expense, cleared
  `gbudget add -15 "coffee" --pending` — expense, pending

**`list [--month YYYY-MM] [-c CAT] [--status pending|cleared]`**
  Show transactions in a table.
  Examples:
  `gbudget list` — all transactions
  `gbudget list --month 2026-07 -c Food` — July food only
  `gbudget list --status pending` — uncleared items

**`summary [--month YYYY-MM] [--by-category]`**
  Show total income, expenses, and net. Add `--by-category` for a breakdown.
  Example: `gbudget summary --month 2026-07 --by-category`

**`edit ID`** with any of `[-a AMOUNT] [-d DESC] [-c CAT] [--type income|expense] [--status cleared]`
  Update specific fields of a transaction. Unused fields stay unchanged.
  Example: `gbudget edit 1 -c Household --status cleared`

**`delete ID`**
  Permanently remove a transaction.
  Example: `gbudget delete 1`

**`clear ID [ID ...]`**
  Move pending transactions to cleared (confirmed by your bank). IDs come from `gbudget list`.
  Example: `gbudget clear 1 2 3`

**`export [--month YYYY-MM]`**
  Regenerate the monthly markdown statement. Defaults to current month.
  Example: `gbudget export --month 2026-07`

**`config [--vault PATH]`**
  View current settings or update the vault path.
  Examples:
  `gbudget config` — show settings
  `gbudget config --vault ~/Documents/Notes` — update vault path

**`recurring`**
  Manage recurring bills and income. Subcommands:
  - `recurring add 12 "Netflix" -c Subscriptions -d 15` — create a template (use `--income` for income)
  - `recurring list` — show all templates with total monthly outgoings
  - `recurring delete 1` — remove a template

## Workflow

1. **Init** — `gbudget init --vault ~/notes` (one-time setup)
2. **Add transactions** — `gbudget add -50 "groceries"` as you spend/earn. New items are saved as **cleared** by default. Use `--pending` for charges that haven't hit your bank yet.
3. **Recurring** — Define regular bills with `gbudget recurring add`. They auto-generate as pending at the start of each month.
4. **Reconcile** — Once a month, check your real bank statement. For each pending item that has gone through, run `gbudget clear 1 2 3` (where `1 2 3` are the transaction IDs from `gbudget list`) to mark them **cleared**.
5. **Statement** — The markdown file at `~/notes/files/money/` updates automatically — cleared transactions appear in the main table, pending ones are listed separately.
6. **Monthly close** — At month end, the app prompts you to generate a final statement and create next month's recurring items.

## Pending vs Cleared

- **Cleared (default)** — A transaction you've added is automatically marked as cleared. Most transactions go through your bank immediately, so this saves you a step.
- **Pending** — Use `--pending` when you add a transaction that hasn't hit your account yet (e.g., a future-dated payment, or a card charge that's still processing).
- **`clear 1 2`** — Moves pending transactions to cleared once they're confirmed by your bank.

## Recurring transactions

Define templates for regular bills or income (rent, Netflix, salary, etc.). On the first CLI run of each month, you'll be prompted to generate them automatically.

Recurring items are created as pending transactions — you still `clear` them when they hit your bank account, just like any other transaction.

## Auto-export

The markdown statement in your vault updates automatically whenever you `add`, `edit`, `delete`, or `clear` transactions. No need to manually run `export` — it's always current.

Run `export` manually if you want to regenerate a past month's statement.
