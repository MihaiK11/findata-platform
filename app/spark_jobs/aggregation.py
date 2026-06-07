from __future__ import annotations

import logging
import os

from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, max, min

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_aggregation() -> None:
    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DB_NAME", "financial_dw")

    if not mongo_url:
        raise ValueError(
            "MONGODB_URL environment variable not set"
        )

    client = MongoClient(mongo_url)
    spark = None

    try:
        logger.info(
            "Loading time-series data from MongoDB..."
        )

        rows = list(
            client[db_name].time_series.find(
                {"is_deleted": False}
            )
        )

        if not rows:
            logger.warning(
                "No time-series data found."
            )
            return

        logger.info(
            "Creating Spark session..."
        )

        spark = (
            SparkSession.builder
            .appName("FinancialAggregation")
            .getOrCreate()
        )

        logger.info(
            "Creating Spark DataFrame..."
        )

        df = spark.createDataFrame(rows)

        logger.info(
            "Computing aggregation statistics..."
        )

        stats = (
            df.groupBy("symbol")
            .agg(
                avg("close").alias("mean_price"),
                min("close").alias("min_price"),
                max("close").alias("max_price"),
            )
        )

        results = [
            row.asDict()
            for row in stats.collect()
        ]

        if not results:
            logger.warning(
                "No aggregation results generated."
            )
            return

        logger.info(
            "Writing %s aggregation records to MongoDB...",
            len(results),
        )

        analytics_collection = (
            client[db_name]
            .analytics_results
        )

        analytics_collection.delete_many({})

        analytics_collection.insert_many(
            results
        )

        logger.info(
            "Aggregation completed successfully."
        )

    except Exception as exc:
        logger.exception(
            "Aggregation job failed: %s",
            exc,
        )
        raise

    finally:
        if spark is not None:
            try:
                spark.stop()
            except Exception:
                pass

        client.close()


if __name__ == "__main__":
    run_aggregation()