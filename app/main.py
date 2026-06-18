import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import redis_manager
from app.models import Order, Outbox

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup infrastructure connections on startup
    redis_manager.connect()
    await redis_manager.register_lua_script()
    # Pre-seed stock for testing purposes (Item: 'ps5_pro' with 100 units available)
    await redis_manager.client.set("item:ps5_pro", 100)
    yield
    await redis_manager.client.close()

app = FastAPI(title="High-Concurrency Booking Engine", lifespan=lifespan)

class BookingRequest(BaseModel):
    user_id: str
    item_id: str

@app.post("/api/v1/book", status_code=status.HTTP_201_CREATED)
async def book_item(request: BookingRequest, db: AsyncSession = Depends(get_db)):
    redis_item_key = f"item:{request.item_id}"
    
    # 1. Memory-Tier Atomic Inventory Check & Decrement via Lua
    stock_secured = await redis_manager.eval_stock_decrement(redis_item_key)
    
    if not stock_secured:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail="Inventory exhausted or item unavailable."
        )
    
    # Generate unique Identifiers for consistency tracking
    order_id = uuid.uuid4()
    
    # 2. Transactional Outbox Block
    try:
        # Define New Order Entity
        new_order = Order(
            id=order_id,
            user_id=request.user_id,
            item_id=request.item_id,
            status="RESERVED"
        )
        
        # Define Outbox Event Payload to be exported asynchronously to Kafka later
        outbox_event = Outbox(
            id=uuid.uuid4(),
            aggregate_type="Order",
            aggregate_id=str(order_id),
            event_type="OrderCreated",
            payload={
                "order_id": str(order_id),
                "user_id": request.user_id,
                "item_id": request.item_id,
                "status": "RESERVED"
            }
        )
        
        # Add both records to the unit of work inside the same atomic PostgreSQL boundary
        db.add(new_order)
        db.add(outbox_event)
        
        # Flush and commit to physical disk storage
        await db.commit()
        
    except Exception as db_error:
        # 3. Compensating Transaction: Roll back memory tier counter if persistent storage fails
        await db.rollback()
        await redis_manager.increment_stock_compensate(redis_item_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System error encountered during checkout recording: {str(db_error)}"
        )

    return {"status": "SUCCESS", "order_id": str(order_id), "message": "Inventory locked and order safely staged."}