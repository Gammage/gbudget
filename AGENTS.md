# gbudget — Personal CLI Budget App

## Architecture

Python 3.13, stdlib only (`argparse`, `sqlite3`, `datetime`).

### Data flow

```
CLI (main.py) → database.py (SQLite) → ~/.local/share/gbudget/budget.db
                                     → ~/notes/Money/YYYY-MM-statement.md
```

### Module layout

```
main.py        — argparse dispatch + auto-prompt (first-run-of-month)
database.py    — SQLite init, CRUD helpers
models.py      — Transaction dataclass
exporters.py   — Markdown statement builder
config.py      — XDG config file management
```

### File locations

| What | Where |
|---|---|
| Database | `~/.local/share/gbudget/budget.db` |
| Config | `~/.config/gbudget/config.json` |
| Statements | `~/notes/files/money/YYYY-MM-statement.md` |

### Config (`~/.config/gbudget/config.json`)

```json
{
  "vault_path": "~/notes",
  "statement_day": 1,
  "last_statement_month": "2026-06"
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
```

---

## CLI Commands

| Command | Description |
|---|---|
| `init --vault PATH` | First-time setup: creates config, DB, and vault folder |
| `add AMOUNT DESC [-c CAT] [-d DATE] [--pending]` | Add a transaction (negative amount → type=expense; positive → income). Defaults to cleared; `--pending` marks as uncleared |
| `list [--month YYYY-MM] [-c CAT] [--status pending \| cleared]` | Tabular output of transactions |
| `summary [--month YYYY-MM]` | Total income, expenses, net. `--by-category` for breakdown |
| `edit ID [-a AMOUNT] [-d DESC] [-c CAT] [--type income \| expense] [--status cleared]` | Edit a transaction |
| `delete ID` | Delete a transaction |
| `clear ID [ID ...]` | Mark one or more transactions as cleared (reconciled) |
| `export [--month YYYY-MM]` | Force-regenerate the monthly statement markdown |
| `config [--vault PATH]` | View current settings or update vault path |
| `recurring add AMT DESC -c CAT -d DAY [--income]` | Create a recurring template |
| `recurring list` | Show all recurring templates with total |
| `recurring delete ID` | Delete a recurring template |

### Auto-prompt behavior

On any command invocation, if the current month differs from `last_statement_month` (in config), two prompts fire:

1. > Generate statement for [last month]? [y/N]
   If yes → export for last month.

2. > Generate recurring transactions for [this month]? [y/N]
   If yes → create pending transactions for each due recurring template.
   Skips any that already exist in the current month (same amount + description).

Updates `last_statement_month` in config after both prompts.

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

## Transactions (Cleared)

| Date | Description | Category | Amount |
|---|---|---|---|
| Jul 3 | Groceries | Food | -£85.00 |
| Jul 4 | Monthly salary | Income | +£2,500.00 |

## Expenses by Category

| Category | Spent | % of Total |
|---|---|---|
| Food | £320.00 | 36% |
| Transport | £150.00 | 17% |

## Pending Transactions

| Date | Description | Category | Amount |
|---|---|---|---|
| Jul 8 | Amazon order | Shopping | -£45.00 |
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
