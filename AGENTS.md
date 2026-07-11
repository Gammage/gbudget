# gbudget — Personal CLI Budget App

## Architecture

Python 3.13, stdlib only (`argparse`, `sqlite3`, `datetime`).

### Data flow

```
CLI (main.py) → database.py (SQLite) → ~/.local/share/gbudget/budget.db
                                     → ~/notes/files/money/YYYY-MM-statement.md (if enabled)
```

### Module layout

```
main.py        — argparse dispatch + auto-prompt (first-run-of-month)
database.py    — SQLite init, CRUD helpers
models.py      — Transaction + Debt dataclasses
exporters.py   — Markdown statement builder
config.py      — XDG config file management
```

### File locations

| What | Where |
|---|---|
| Database | `~/.local/share/gbudget/budget.db` |
| Config | `~/.config/gbudget/config.json` |
| Statements | `~/notes/files/money/YYYY-MM-statement.md` (only if enabled) |

### Config (`~/.config/gbudget/config.json`)

```json
{
  "vault_path": "",
  "statement_day": 1,
  "last_statement_month": "",
  "statements_enabled": false
}
```

---

## Schema

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    date TEXT NOT NULL,                        -- YYYY-MM-DD
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'cleared')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE recurring (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL CHECK(amount > 0),
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'General',
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    day INTEGER NOT NULL CHECK(day BETWEEN 1 AND 28),
    last_generated TEXT,                       -- YYYY-MM of last auto-generation
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    initial_amount REAL NOT NULL CHECK(initial_amount > 0),
    annual_rate REAL NOT NULL DEFAULT 0 CHECK(annual_rate >= 0),
    start_date TEXT NOT NULL,                  -- YYYY-MM-DD
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paid_off')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE debt_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    debt_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    fee REAL NOT NULL DEFAULT 0 CHECK(fee >= 0),
    date TEXT NOT NULL,                        -- YYYY-MM-DD
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (debt_id) REFERENCES debts(id) ON DELETE CASCADE
);
```

---

## CLI Commands

| Command | Description |
|---|---|
| `init` | First-time setup: creates config and DB |
| `add AMOUNT DESC [-c CAT] [-d DATE] [--pending]` | Add a transaction (negative amount → type=expense; positive → income). Defaults to cleared; `--pending` marks as uncleared |
| `list [--month YYYY-MM] [-c CAT] [--status pending \| cleared]` | Tabular output of transactions |
| `summary [--month YYYY-MM]` | Total income, expenses, net. `--by-category` for breakdown |
| `edit ID [-a AMOUNT] [-d DESC] [-c CAT] [--type income \| expense] [--status cleared]` | Edit a transaction |
| `delete ID` | Delete a transaction |
| `clear ID [ID ...]` | Mark one or more transactions as cleared (reconciled) |
| `setup-statements --vault PATH` | Enable markdown statements (creates `files/money/` dir, sets `statements_enabled`) |
| `export [--month YYYY-MM]` | Force-regenerate the monthly statement markdown |
| `config [--vault PATH]` | View current settings or update vault path |
| `recurring add AMT DESC -c CAT -d DAY [--income]` | Create a recurring template |
| `recurring list` | Show all recurring templates with total |
| `recurring delete ID` | Delete a recurring template |
| `reset` | Delete all transactions + recurring templates. If vault statements are enabled, prompts to delete statement files too. Config preserved. |
| `debt add NAME AMOUNT --rate ANNUAL_RATE [-d DATE]` | Add a new debt or loan |
| `debt list` | Show all debts with current balances |
| `debt pay ID AMOUNT [-d DATE]` | Record a payment against a debt (prompts for fee) |
| `debt delete ID` | Delete a debt and its payments |

### Auto-prompt behavior

#### Monthly prompts

On any command invocation, if the current month differs from `last_statement_month` (in config), prompts fire:

1. > Generate statement for [last month]? [y/N]
   Only shown when `statements_enabled` is `true`. If yes → export for last month.

2. > Generate recurring transactions for [this month]? [y/N]
   Always shown (regardless of statements). If yes → create pending transactions for each due recurring template.
   Skips any that already exist in the current month (same amount + description).

Updates `last_statement_month` in config after both prompts.

#### Reset prompts

On `gbudget reset`:
1. > Continue? [Y/N]
   Confirmation before deleting all data. Abort on any response other than `Y`.

2. > Delete vault statement files too? [Y/N]
   Only shown when `vault_path` is set and `statements_enabled` is `true`. If yes → deletes `files/money/` directory and disables statements.

Config (`vault_path`, `statement_day`) is always preserved. `last_statement_month` is cleared to `""`.

#### Debt payment prompts

On `gbudget debt pay ID AMOUNT`:
1. > Enter fee for payment to "<debt name>" (0 if none): 
   Prompts for transfer fee. Enter `0` if no fee. Stored in `debt_payments.fee`.

If balance drops to £0 or below after payment, debt status is set to `paid_off`.

---

## Statement Format (`~/notes/files/money/YYYY-MM-statement.md`)

```markdown
---
id: 2026-07-statement
aliases: []
tags:
  - money
  - budget
  - statement
---

# Monthly Statement — July 2026

**Period:** Jul 1 – Jul 31, 2026
**Generated:** Jul 9, 2026

## Account Overview

| | Amount |
|---|---|
| Opening Balance | £1,200.00 |
| Income | £2,500.00 |
| Expenses | -£890.00 |
| **Net Change** | **+£1,610.00** |
| **Closing Balance** | **£2,810.00** |
| **Saved this month** | **£1,610.00** |

## Recurring Payments

| Description | Category | Amount | Due Day |
|---|---|---|---|
| Rent | Housing | -£500.00 | 1 |
| Netflix | Subscriptions | -£12.00 | 15 |

**Total outgoings:** -£512.00

## Transactions (Cleared)

| Date | Description | Category | Amount |
|---|---|---|---|
| Jul 3 | Groceries | Food | -£85.00 |
| Jul 4 | Monthly salary | Income | +£2,500.00 |

**Total:** +£2,415.00

## Expenses by Category

| Category | Spent | % of Total |
|---|---|---|
| Food | £320.00 | 36% |
| Transport | £150.00 | 17% |

## Pending Transactions

| Date | Description | Category | Amount |
|---|---|---|---|
| Jul 8 | Amazon order | Shopping | -£45.00 |

## Debts & Loans

| Debt | Balance | Interest | Payments | New Balance |
|---|---|---|---|---|
| Student Loan | £12,000.00 | +£50.00 | -£200.00 | £11,850.00 |
| Credit Card | £1,500.00 | +£18.75 | -£100.00 | £1,418.75 |

**Total debt:** £13,268.75
```

---

## Future (benched)

- Investment types: `buy`/`sell`/`dividend` with nullable `ticker`, `shares`, `price_per_share` fields
- Portfolio holdings table and DCA performance tracking
- Current price fetching via API
- `gbudget prices` command to update current market prices

## Development

```bash
./gbudget --help
# or
python main.py --help
```

## Testing

Manual testing only — no test framework. Log all test results in `test.md` with:
- Date of testing session
- Commands tested and their output/behavior
- Observations, edge cases, and any issues found
