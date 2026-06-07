from fastapi import APIRouter
import subprocess

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/run-aggregation")
async def run_aggregation():
    subprocess.run(
        ["spark-submit", "app/spark_jobs/aggregation.py"],
        check=True,
    )
    return {"status": "aggregation complete"}


@router.post("/run-forecast")
async def run_forecast():
    subprocess.run(
        ["spark-submit", "app/spark_jobs/forecast.py"],
        check=True,
    )
    return {"status": "forecast complete"}