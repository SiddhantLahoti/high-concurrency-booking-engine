import redis.asyncio as aioredis
from app.config import settings

class RedisManager:
    def __init__(self):
        self.client = None
        self.lua_script_sha = None

    def connect(self):
        self.client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def register_lua_script(self):
        # Lua script ensures reading and modifying the inventory count happens atomically
        # inside Redis single-threaded runtime loop.
        lua_code = """
        local stock = tonumber(redis.call('get', KEYS[1]))
        if stock and stock > 0 then
            redis.call('decr', KEYS[1])
            return 1
        end
        return 0
        """
        self.lua_script_sha = await self.client.script_load(lua_code)

    async def eval_stock_decrement(self, item_key: str) -> int:
        return await self.client.evalsha(self.lua_script_sha, 1, item_key)

    async def increment_stock_compensate(self, item_key: str):
        await self.client.incr(item_key)

redis_manager = RedisManager()