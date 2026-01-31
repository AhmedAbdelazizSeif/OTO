import asyncio
from API import OTOAsyncClient


async def main():
    async with OTOAsyncClient(refresh_token="AMf-vBwu8e_RojO6vqCd9ZypYrqwau_cXUKptqGfXfMFPiQK759oC0kqe4ZEn8fIXdPpXw4l2BU7hYZMlcwHTSs3LEp9HIVUjWZqrkVUtKhN_kCxgzMLn11IqoMKiTnkFfm_N0Xz0UkE1ElljaCj3nAEzGbmhvl-LW1lAGmc1v_41TYKjRXalp2S5rc4R7DtVT-oQooHQosHp2gLuo5TScDPAvnxDBHAyg", auto_refresh=True) as client:
        print("Fetching order tracking information...")
        response = await client.get_order_history(['64220660'])
        print("Response:", response)

asyncio.run(main())