from __future__ import annotations

import logging
import os

os.environ["PYSPARK_PYTHON"] = "python"
os.environ["PYSPARK_DRIVER_PYTHON"] = "python"

from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, max, min
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

spark: SparkSession = (
    SparkSession.builder
    .appName("FinancialAnalytics")
    .master("local[*]")
    .config("spark.pyspark.python", "python")
    .config("spark.pyspark.driver.python", "python")
    .getOrCreate()
)


def run_aggregation() -> None:
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
                {"_id": 0}  # remove ObjectId at query level (faster)
            )
        )

        if not rows:
            logger.warning("No time-series data found.")
            return

        logger.info("Normalizing numeric fields...")

        # =========================
        # Data cleaning
        # =========================
        for row in rows:
            for key in ["open", "high", "low", "close", "volume"]:
                if row.get(key) is not None:
                    try:
                        row[key] = float(row[key])
                    except (TypeError, ValueError):
                        row[key] = None

        logger.info("Creating Spark DataFrame...")

        df = spark.createDataFrame(rows)

        # =========================
        # Aggregation
        # =========================
        stats = (
            df.groupBy("symbol")
            .agg(
                avg("close").alias("mean_price"),
                min("close").alias("min_price"),
                max("close").alias("max_price"),
            )
        )

        results = [row.asDict() for row in stats.collect()]

        logger.info("Writing %s analytics records to MongoDB...", len(results))

        analytics = client[db_name].analytics_results

        analytics.delete_many({})

        if results:
            analytics.insert_many(results)

        logger.info("Aggregation complete. %s records written.", len(results))

    except Exception as exc:
        logger.exception("Aggregation job failed: %s", exc)
        raise

    finally:
        client.close()
        spark.stop()


if __name__ == "__main__":
    run_aggregation()