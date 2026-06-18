from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# Create asynchronous engine connection
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10)

# Session factory for generating clean single-request database contexts
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session