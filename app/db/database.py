from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = None

async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    print("Connected to MongoDB")

async def close_db():
    global client
    if client:
        client.close()

def get_database():
    return client[settings.db_name]