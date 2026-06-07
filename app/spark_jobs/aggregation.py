from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, min, max

import os

MONGO_URL = os.getenv("MONGODB_URL")
DB_NAME = os.getenv("DB_NAME", "financial_dw")

if not MONGO_URL:
    raise ValueError("MONGODB_URL environment variable not set")

client = MongoClient(MONGO_URL)

rows = list(
    client[DB_NAME].time_series.find(
        {"is_deleted": False}
    )
)

spark = (
    SparkSession.builder
    .appName("FinancialAggregation")
    .getOrCreate()
)

df = spark.createDataFrame(rows)

stats = df.groupBy("symbol").agg(
    avg("close").alias("mean_price"),
    min("close").alias("min_price"),
    max("close").alias("max_price"),
)

for row in stats.collect():
    client[DB_NAME].analytics_results.insert_one(
        row.asDict()
    )

print("Aggregation complete")