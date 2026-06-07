from __future__ import annotations

import logging
import os
from pymongo import MongoClient

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
from pyspark.sql.functions import col, avg

from app.config import settings

# ----------------------------
# FIX Spark Python on Windows
# ----------------------------
os.environ["PYSPARK_PYTHON"] = "python"
os.environ["PYSPARK_DRIVER_PYTHON"] = "python"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------
# Spark Session
# ----------------------------
spark = (
    SparkSession.builder
    .appName("FinancialForecast")
    .master("local[*]")
    .config("spark.pyspark.python", "python")
    .config("spark.pyspark.driver.python", "python")
    .getOrCreate()
)


# =========================================================
# REUSED MONGO LOADER (based on aggregation.py)
# =========================================================
def load_time_series_from_mongo():
    mongo_url = settings.mongodb_url
    db_name = settings.db_name

    if not mongo_url:
        raise ValueError("MONGODB_URL environment variable not set")

    client = MongoClient(mongo_url)

    try:
        logger.info("Loading time-series data from MongoDB...")

        collection = client[db_name].time_series

        rows = list(
            collection.find(
                {"is_deleted": False},
                {"_id": 0}
            )
        )

        if not rows:
            logger.warning("No time-series data found.")
            return []

        logger.info("Normalizing numeric fields...")

        for row in rows:
            for key in ["open", "high", "low", "close", "volume"]:
                if row.get(key) is not None:
                    try:
                        row[key] = float(row[key])
                    except (TypeError, ValueError):
                        row[key] = None

        return rows

    finally:
        client.close()


# =========================================================
# FORECAST LOGIC
# =========================================================
def build_forecast(df):
    """
    Simple forecasting baseline:
    - mean close price per symbol
    - can be replaced with ML model later
    """

    logger.info("Building forecast...")

    forecast_df = (
        df.groupBy("symbol")
        .agg(
            avg(col("close")).alias("predicted_price")
        )
    )

    return forecast_df


# =========================================================
# MAIN PIPELINE
# =========================================================
def run_forecast():
    try:
        # 1. Load data (NOW SAME AS aggregation.py STYLE)
        rows = load_time_series_from_mongo()

        if not rows:
            logger.warning("No data to forecast.")
            return []

        # 2. Explicit schema (prevents DoubleType/LongType crash)
        schema = StructType([
            StructField("symbol", StringType(), True),
            StructField("open", DoubleType(), True),
            StructField("high", DoubleType(), True),
            StructField("low", DoubleType(), True),
            StructField("close", DoubleType(), True),
            StructField("volume", DoubleType(), True),
        ])

        logger.info("Creating Spark DataFrame...")
        df = spark.createDataFrame(rows, schema=schema)

        df.show()

        # 3. Forecast
        forecast = build_forecast(df)

        logger.info("Forecast results:")
        forecast.show()

        # 4. Collect results
        results = [r.asDict() for r in forecast.collect()]

        logger.info("Forecast completed successfully.")
        return results

    except Exception as e:
        logger.exception(f"Forecast job failed: {e}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    run_forecast()