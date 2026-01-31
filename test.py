import asyncio
from API import OTOAsyncClient
import os


async def main():
    async with OTOAsyncClient(refresh_token=os.getenv("OTO_REFRESH_TOKEN"), auto_refresh=True) as client:
        print("Fetching order tracking information...")
        response = await client.get_order_history(['64220660'])
        print("Response:", response)

asyncio.run(main())