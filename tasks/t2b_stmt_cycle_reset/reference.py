"""Executable legacy oracle for t2b_stmt_cycle_reset.
Cursor semantics: cycle counter starts at 1 per account; a STMT row FIRST
resets the balance and increments the cycle, THEN adds its own amount (the
statement fee posts into the new cycle)."""
import pandas as pd

def run(inputs):
    df = inputs["ledger"].sort_values(
        ["account_id", "entry_date", "row_seq"]).copy()
    is_stmt = (df["entry_type"] == "STMT").astype(int)
    df["cycle_no"] = 1 + is_stmt.groupby(df["account_id"]).cumsum()
    df["cycle_balance"] = (df["amount"].fillna(0)
                           .groupby([df["account_id"], df["cycle_no"]]).cumsum())
    return {"cycle_balances": df[["account_id", "row_seq", "entry_date",
                                  "entry_type", "amount", "cycle_no",
                                  "cycle_balance"]]}
