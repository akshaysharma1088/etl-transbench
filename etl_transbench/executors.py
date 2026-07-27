"""Execution engines for candidate translations.

The equivalence checker is engine-agnostic (pandas DataFrames at the
boundary); executors adapt engines to that boundary.

- PandasExecutor: runs candidates whose run() consumes/produces pandas frames.
- SparkExecutor:  runs PySpark candidates. The candidate module must define
      run(spark, inputs: dict[str, pyspark.sql.DataFrame])
          -> dict[str, pyspark.sql.DataFrame]
  Inputs are pandas frames converted to Spark DataFrames; outputs are
  collected back to pandas for comparison. A single local[2] session is
  shared across calls (Spark session startup dominates otherwise).

For the paper's experiments the TARGET dialect is PySpark; pandas tasks in
this scaffold are the development stand-in, and the same task definitions
work under SparkExecutor by translating to the Spark entry signature.
"""
from __future__ import annotations
import traceback
from typing import Any, Callable, Dict, Tuple

import pandas as pd


class PandasExecutor:
    name = "pandas"

    def execute(self, run_fn, inputs: Dict[str, pd.DataFrame]
                ) -> Tuple[Dict[str, pd.DataFrame] | None, str]:
        try:
            return run_fn({k: v.copy() for k, v in inputs.items()}), ""
        except Exception:
            return None, traceback.format_exc(limit=5)


def _null_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Map pandas missing values to true nulls before Spark ingestion.

    FINDING (record in paper Sec. 3.2 / 7): pandas represents missing floats
    as NaN, and float columns silently coerce None back to NaN. Spark SQL
    treats NaN as a VALUE that sorts greater than every number, so a legacy
    `WHERE amount > 100` (NULL filtered out) becomes `NaN > 100 == true`
    in Spark — the row survives and even lands in the top size band. The
    ingestion boundary must therefore convert NaN in float columns to Spark
    nulls explicitly; this single line is the difference between a correct
    and a silently wrong migration, and our differential harness caught it
    on the first cross-engine run.
    """
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].astype(object).where(out[c].notna(), None)
        elif (out[c].dtype == object or pd.api.types.is_string_dtype(out[c])
              or str(out[c].dtype).startswith("Int")):
            # NOTE: pandas 3.x 'str' dtype cannot hold None (coerces to NaN,
            # which Spark renders as the literal string 'nan'): cast to object
            # BEFORE substituting None. Second ingestion hazard caught by the
            # differential harness.
            out[c] = out[c].astype(object).where(out[c].notna(), None)
    return out


class SparkExecutor:
    name = "pyspark"
    _spark = None

    @classmethod
    def session(cls):
        if cls._spark is None:
            from pyspark.sql import SparkSession
            cls._spark = (SparkSession.builder
                          .master("local[2]")
                          .appName("etl-transbench")
                          .config("spark.ui.enabled", "false")
                          .config("spark.sql.shuffle.partitions", "4")
                          .config("spark.sql.session.timeZone", "UTC")
                          .getOrCreate())
        return cls._spark

    def execute(self, run_fn, inputs: Dict[str, pd.DataFrame]
                ) -> Tuple[Dict[str, pd.DataFrame] | None, str]:
        spark = self.session()
        try:
            sdf_inputs = {k: spark.createDataFrame(_null_safe(v))
                          for k, v in inputs.items()}
            out = run_fn(spark, sdf_inputs)
            return {k: v.toPandas() for k, v in out.items()}, ""
        except Exception:
            return None, traceback.format_exc(limit=5)

    @classmethod
    def stop(cls):
        if cls._spark is not None:
            cls._spark.stop()
            cls._spark = None


def compile_spark_candidate(code: str) -> Tuple[Callable | None, str]:
    """Compile a PySpark candidate module defining run(spark, inputs)."""
    ns: Dict[str, Any] = {}
    try:
        exec(compile(code, "<spark_candidate>", "exec"), ns)  # noqa: S102 sandbox in prod
    except Exception:
        return None, traceback.format_exc(limit=5)
    fn = ns.get("run")
    if not callable(fn):
        return None, "candidate does not define callable 'run(spark, inputs)'"
    return fn, ""
