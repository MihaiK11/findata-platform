from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.functions import monotonically_increasing_id
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression

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
    .appName("ForecastModel")
    .getOrCreate()
)

df = spark.createDataFrame(rows)

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

for row in predictions.select(
    "symbol",
    "prediction"
).collect():

    client[DB_NAME].forecast_results.insert_one(
        row.asDict()
    )

print("Forecast complete")