from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import monotonically_increasing_id
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression

import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_forecast() -> None:
    mongo_url = os.getenv("MONGODB_URL")
    db_name = os.getenv("DB_NAME", "financial_dw")

    if not mongo_url:
        raise ValueError("MONGODB_URL environment variable not set")

    client = MongoClient(mongo_url)
    spark = None

    try:
        logger.info("Loading time-series data from MongoDB...")

        rows = list(
            client[db_name].time_series.find(
                {"is_deleted": False}
            )
        )

        if not rows:
            logger.warning("No time-series data found.")
            return

        spark = (
            SparkSession.builder
            .appName("ForecastModel")
            .getOrCreate()
        )

        df = spark.createDataFrame(rows)

        logger.info("Creating features...")

        df = df.withColumn(
            "day_index",
            monotonically_increasing_id()
        )

        assembler = VectorAssembler(
            inputCols=["day_index"],
            outputCol="features"
        )

        training = assembler.transform(df)

        lr = LinearRegression(
            featuresCol="features",
            labelCol="close"
        )

        model = lr.fit(training)

        predictions = model.transform(training)

        results = []
        for row in predictions.select("symbol", "prediction").collect():
            try:
                results.append(row.asDict())
            except Exception as e:
                logger.warning("Skipping row due to error: %s", e)

        if results:
            client[db_name].forecast_results.delete_many({})
            client[db_name].forecast_results.insert_many(results)

        logger.info("Forecast complete. %s predictions written.", len(results))

    except Exception as e:
        logger.exception("Forecast job failed: %s", e)
        raise

    finally:
        if spark is not None:
            spark.stop()
        client.close()


if __name__ == "__main__":
    run_forecast()