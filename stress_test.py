import asyncio
import httpx
import time

URL = "http://127.0.0.1:8000/api/v1/book"
# We will simulate 200 users hitting the endpoint simultaneously
TOTAL_USERS = 200 

async def send_booking_request(client, user_id):
    payload = {
        "user_id": f"user_{user_id}",
        "item_id": "ps5_pro"
    }
    try:
        response = await client.post(URL, json=payload, timeout=10.0)
        return response.status_code
    except Exception as e:
        return f"Failed: {str(e)}"

async def main():
    print(f"🚀 Preparing to blast the engine with {TOTAL_USERS} concurrent requests...")
    
    # Create an asynchronous HTTP client
    async with httpx.AsyncClient() as client:
        # Create a list of 200 unique user request tasks
        tasks = [send_booking_request(client, i) for i in range(1, TOTAL_USERS + 1)]
        
        start_time = time.time()
        # Fire ALL 200 requests simultaneously!
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
    # Analyze the aftermath
    duration = end_time - start_time
    success_count = results.count(201)
    sold_out_count = results.count(422)
    error_count = len(results) - (success_count + sold_out_count)
    
    print("\n📊 --- STRESS TEST RESULTS ---")
    print(f"⏱️  Total Time Taken: {duration:.2f} seconds")
    print(f"⚡ Requests Per Second: {TOTAL_USERS / duration:.2f}")
    print(f"✅ Successful Orders (201 Created): {success_count}")
    print(f"❌ Rejected Orders (422 Sold Out): {sold_out_count}")
    print(f"🔥 System Crashes/Errors: {error_count}")
    
    print("\n💡 Architectural Verification:")
    if success_count == 100:
        print("🏆 SUCCESS: Perfect Inventory Isolation! Exactly 100 items were sold.")
    elif success_count > 100:
        print(f"🚨 CRITICAL FAILURE: Oversold! You sold {success_count} items but only had 100.")
    else:
        print(f"⚠️  UNDER-ALLOCATION: Only sold {success_count}. Check for system bottlenecks.")

if __name__ == "__main__":
    asyncio.run(main())