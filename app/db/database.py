from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_url)
    print("✓ Connected to MongoDB")

    # initialize collections and indexes
    from app.db.db_collections import init_collections
    await init_collections()


async def close_db():
    global client
    if client:
        client.close()
        print("✓ MongoDB connection closed")


def get_database():
    return client[settings.db_name]