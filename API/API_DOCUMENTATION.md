# OTO API Python Wrapper Documentation

## Overview
This is a fully typed, asynchronous Python client for the OTO Logistics API V2. It is built using `httpx` and `pydantic`, providing robustness, autocompletion, and easy error handling.

## Installation

Ensure you have Python 3.8+ installed.

1. Install dependencies:
   ```bash
   pip install -r API/requirements.txt
   ```

## Getting Started

### Initialization
To use the client, you need a **Refund Token** (Refresh Token) from your OTO dashboard.

```python
import asyncio
from API.client import OTOAsyncClient

async def main():
    # Initialize with your refresh token
    async with OTOAsyncClient(refresh_token="YOUR_REFRESH_TOKEN") as client:
        # Client automatically handles access token retrieval and refreshing
        print(f"Token expires at: {client.token_expires_at()}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Basic Example: Creating an Order

```python
from API.models import CreateOrderRequest, PaymentMethod, Customer, OrderItem

async def create_new_order(client):
    request = CreateOrderRequest(
        order_id="ORD-2024-001",
        payment_method=PaymentMethod.COD,
        amount=150.0,
        amount_due=150.0,
        currency="SAR",
        customer=Customer(
            name="John Doe",
            mobile="+966500000000",
            address="123 Main St",
            city="Riyadh",
            country="SA"
        ),
        items=[
            OrderItem(
                product_id="PROD-123",
                name="Wireless Headphones",
                price=150.0,
                quantity=1
            )
        ]
    )
    
    response = await client.create_order(request)
    if response.success:
        print("Order created successfully!")
    else:
        print(f"Failed: {response.message}")
```

## Error Handling

The client uses custom exceptions defined in `API/exceptions.py`. You should wrap your API calls in try/except blocks.

```python
from API.exceptions import (
    OTOAuthenticationError,
    OTOValidationError,
    OTONetworkError
)

try:
    await client.create_order(request)
except OTOValidationError as e:
    print(f"Invalid data: {e}")
except OTOAuthenticationError:
    print("Authentication failed - check your token")
except OTONetworkError:
    print("Network issue - please retry")
```

---

## API Reference

### 1. Order Management

#### `create_order(request: CreateOrderRequest) -> CreateOrderResponse`
Create a new order in OTO.
- **request**: Detailed order information including customer and items.

#### `update_order(request: UpdateOrderRequest) -> UpdateOrderResponse`
Update an existing order (e.g., address, notes) before shipment.

#### `cancel_order(order_id: str) -> SuccessResponse`
Cancel an order. *Note: Cannot cancel if a shipment has already been created.*

#### `get_orders(...) -> GetOrdersResponse`
Search and filter orders.
- **Parameters**: `status`, `from_date`, `to_date`, `page`, `per_page`, etc.

#### `get_order_details(order_id: str) -> OrderDetailsResponse`
Get full details for a single order, including status history.

#### `check_order_availability(request)`
Check if an order can be fulfilled based on inventory rules.

### 2. Shipment Management

#### `create_shipment(request: CreateShipmentRequest) -> CreateShipmentResponse`
Generate a shipment for an order.
- **request**: Requires `order_id` and optionally `delivery_option_id`.

#### `cancel_shipment(order_id, shipment_id) -> SuccessResponse`
Cancel an active shipment (if not yet picked up).

#### `track_shipment(request: TrackShipmentRequest) -> TrackShipmentResponse`
Track a shipment using the carrier's tracking number.

#### `print_awb(order_id: str) -> PrintAWBResponse`
Get the PDF URL for the shipping label (Air Waybill).

### 3. Returns & Reverse Logistics

#### `create_return_shipment(request)`
Initiate a return shipment from the customer to the warehouse.

#### `get_return_link(order_id)`
Generate a self-service return portal link for the customer.

#### `trigger_return_sms(order_id)`
Send an SMS to the customer with return instructions.

### 4. Inventory & Products

#### `create_product(request: CreateProductRequest)`
Add a new product to the catalog.

#### `update_stock_quantity(request: UpdateStockQuantityRequest)`
Update inventory levels (set, increment, or decrement) for a SKU.

#### `get_products(page_size, current_page)`
List all products in the catalog.

### 5. Delivery & Coverage

#### `check_oto_delivery_fee(request)`
Get rates from OTO's marketplace carriers.

#### `check_delivery_fee(request)`
Get rates from your own contracted carriers.

#### `check_coverage(request)`
Verify if a delivery route is covered.

### 6. Locations

#### `create_pickup_location(request)`
Add a new warehouse or branch.

#### `get_pickup_locations()`
List all configured pickup locations.

---

## Data Models

All models are Pydantic V2 models, ensuring type safety.

- **Request Models**: Used for input arguments (e.g., `CreateOrderRequest`).
- **Response Models**: Returned by API methods (e.g., `CreateOrderResponse`).
- **Enums**: Constants for fixed values (e.g., `PaymentMethod.COD`, `OrderStatus.DELIVERED`).

### Key Enums
- **PaymentMethod**: `cod`, `paid`
- **PickingType**: `PICKUP_BY_DC`, `BRANCH_DROP_OFF`
- **DeliveryType**: `toCustomerDoorstep`, `pickupByCustomer`

## Support
For API support, please refer to the official OTO documentation or contact support.
