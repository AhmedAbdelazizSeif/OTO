# OTO Python Client

A fully typed, asynchronous Python client for the OTO Logistics API v2, built with `httpx` and `pydantic`. It handles token refresh for you and covers orders, shipments, returns, delivery fees, pickup locations, products and stock.

Built to plug a 3PL layer into an Odoo-style ERP: create and track shipments, and keep inventory in sync from one place.

## What's inside

- `API/` - the client, request/response models, exceptions and an adapter layer. See [`API/API_DOCUMENTATION.md`](API/API_DOCUMENTATION.md) for usage and [`API/docs/`](API/docs) for the client and model references.
- `mcp-server/` - an MCP server that exposes the client as tools, plus a searchable Q&A knowledge base. See [`mcp-server/README.md`](mcp-server/README.md).
- `oto.yaml` - OpenAPI description of the OTO API v2, used as the reference.
- `API_COMPATIBILITY_REPORT.md` - notes on how the client lines up with the API spec.

## Quick start

```bash
pip install -r API/requirements.txt
```

```python
import asyncio
from API.client import OTOAsyncClient

async def main():
    async with OTOAsyncClient(refresh_token="YOUR_REFRESH_TOKEN") as client:
        print(client.token_expires_at())

asyncio.run(main())
```

You get the refresh token from your own OTO dashboard. Never commit it.
