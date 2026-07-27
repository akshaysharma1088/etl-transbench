"""Executable legacy oracle for t1_dialect_qualify (DuckDB supports QUALIFY,
giving us a faithful executable stand-in for the legacy engine)."""
import duckdb, os

def run(inputs):
    con = duckdb.connect()
    con.register("acct_txn", inputs["acct_txn"])
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "legacy_artifact.sql")) as f:
        sql = "".join(l for l in f if not l.strip().startswith("--"))
    out = con.execute(sql).df()
    return {"latest_high_value_txn": out}
