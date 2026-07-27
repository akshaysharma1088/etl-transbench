"""Spark executor test: a genuine PySpark translation of the T1 task,
executed on local Spark and verified for data equivalence against the
DuckDB legacy oracle. Demonstrates the full legacy-engine -> Spark-target
differential pipeline the paper describes."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from etl_transbench.harness import Task
from etl_transbench.executors import SparkExecutor, compile_spark_candidate
from etl_transbench.equivalence import compare_outputs

T1_SPARK = '''
from pyspark.sql import functions as F, Window

def run(spark, inputs):
    df = inputs["acct_txn"]
    df = df.filter(F.col("amount") > 100)
    w = Window.partitionBy("account_id").orderBy(F.col("txn_ts").desc(),
                                                 F.col("txn_id").desc())
    df = df.withColumn("rn", F.row_number().over(w)).filter(F.col("rn") == 1).drop("rn")
    df = df.withColumn("size_band",
            F.when(F.col("amount") >= 1000, "JUMBO")
             .when(F.col("amount") >= 500, "LARGE")
             .otherwise("STANDARD"))
    return {"latest_high_value_txn":
            df.select("account_id","txn_id","txn_ts","amount","channel","size_band")}
'''

if __name__ == "__main__":
    task = Task.load(os.path.join(ROOT, "tasks", "t1_dialect_qualify"))
    fn, err = compile_spark_candidate(T1_SPARK)
    assert fn, err
    ex = SparkExecutor()
    for seed in (11, 23):
        inputs = task.corpus(seed)
        
        clean = inputs  # _null_safe now handled inside SparkExecutor
        ref_out = task.reference({k: v.copy() for k, v in inputs.items()})
        cand_out, exec_err = ex.execute(fn, clean)
        assert cand_out is not None, exec_err
        rep = compare_outputs(ref_out, cand_out, task.spec)
        assert rep["equivalent"], rep
        print(f"PASS  seed {seed}: PySpark translation equivalent to DuckDB legacy oracle")
    SparkExecutor.stop()
    print("\nSPARK EXECUTOR TEST PASSED")
