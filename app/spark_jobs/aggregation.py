from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, min, max

MONGO_URL = "YOUR_MONGODB_URL"
DB_NAME = "YOUR_DB_NAME"

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