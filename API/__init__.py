"""
OTO API V2 Python Client Library.

A production-grade, fully typed async client for the OTO logistics and
fulfillment API. This library provides a clean, Pythonic interface to all
OTO API endpoints with full type safety using Pydantic models.

Features:
- Fully async using httpx
- Complete type annotations
- Pydantic V2 models for all requests/responses
- Automatic token refresh
- Comprehensive exception hierarchy
- Google-style docstrings for MCP introspection

Basic Usage:
    >>> from oto_api import OTOAsyncClient, Customer, OrderItem, CreateOrderRequest
    >>> 
    >>> async with OTOAsyncClient(refresh_token="your_token") as client:
    ...     # Check account info
    ...     info = await client.get_account_info()
    ...     print(f"Credit balance: {info.remaining_credit}")
    ...     
    ...     # Create an order
    ...     order = await client.create_order(CreateOrderRequest(
    ...         order_id="ORD-001",
    ...         payment_method="cod",
    ...         amount=100.0,
    ...         amount_due=100.0,
    ...         currency="SAR",
    ...         customer=Customer(
    ...             name="Ahmed",
    ...             mobile="+966500000000",
    ...             address="123 Main St",
    ...             city="Riyadh",
    ...             country="SA"
    ...         ),
    ...         items=[OrderItem(name="Widget", sku="SKU-001", price=100.0, quantity=1)]
    ...     ))
    ...     print(f"Created order: {order.oto_id}")

Using the convenience function:
    >>> from oto_api import create_client
    >>> 
    >>> async with create_client(refresh_token="your_token") as client:
    ...     orders = await client.get_orders(status="delivered")

Staging Environment:
    >>> from oto_api import OTOAsyncClient
    >>> 
    >>> async with OTOAsyncClient(
    ...     refresh_token="your_token",
    ...     base_url=OTOAsyncClient.STAGING_URL
    ... ) as client:
    ...     health = await client.health_check()

Error Handling:
    >>> from oto_api import OTOAsyncClient, OTOValidationError, OTONotFoundError
    >>> 
    >>> async with OTOAsyncClient(refresh_token="your_token") as client:
    ...     try:
    ...         details = await client.get_order_details("INVALID-ID")
    ...     except OTONotFoundError as e:
    ...         print(f"Order not found: {e.error_message}")
    ...     except OTOValidationError as e:
    ...         print(f"Validation error: {e.error_message}")
"""

__version__ = "1.0.0"
__author__ = "OTO API Client"
__license__ = "MIT"

# Client
from .client import OTOAsyncClient, create_client

# Exceptions
from .exceptions import (
    OTOException,
    OTOAuthenticationError,
    OTOAuthorizationError,
    OTONotFoundError,
    OTOValidationError,
    OTOConflictError,
    OTORateLimitError,
    OTOServerError,
    OTOInsufficientCreditError,
    OTONetworkError,
)

# Enums
from .models import (
    PaymentMethod,
    PickingType,
    WhoPays,
    ServiceType,
    DeliveryType,
    OrderStatus,
    PickupLocationType,
    PickupLocationStatus,
    OnHoldReasonLang,
)

# Core Models
from .models import (
    OTOBaseModel,
    Customer,
    OrderItem,
    SenderInformation,
)

# Authentication Models
from .models import (
    RefreshTokenRequest,
    RefreshTokenResponse,
    HealthCheckResponse,
)

# Account Models
from .models import (
    AccountInfoResponse,
    BuyCreditRequest,
    BuyCreditResponse,
    CreditTransaction,
    CreditTransactionsResponse,
)

# Marketplace Models
from .models import (
    RegisterRequest,
    RegisterResponse,
    ClientInfoRequest,
    ClientInfoResponse,
)

# Order Models
from .models import (
    CreateOrderRequest,
    CreateOrderResponse,
    UpdateOrderRequest,
    UpdateOrderResponse,
    UpdateOrderStatusRequest,
    CancelOrderRequest,
    HoldOrderRequest,
    UnholdOrderRequest,
    StatusHistoryEntry,
    OrderDetailsResponse,
    Order,
    GetOrdersResponse,
    CheckOrderAvailabilityRequest,
    LocationCoordinates,
    AvailableLocation,
    CheckOrderAvailabilityResponse,
)

# Shipment Models
from .models import (
    CreateShipmentRequest,
    CreateShipmentResponse,
    CancelShipmentRequest,
    ShipmentTransaction,
    ShipmentTransactionsResponse,
    GetShippingPriceTransactionsRequest,
    ShippingPriceTransaction,
    GetShippingPriceTransactionsResponse,
)

# Return Shipment Models
from .models import (
    ReturnItem,
    CreateReturnShipmentRequest,
    CreateReturnShipmentResponse,
    GetReturnLinkRequest,
    GetReturnLinkResponse,
    GetReturnDetailsRequest,
    ReturnItemDetail,
    GetReturnDetailsResponse,
    TriggerReturnSmsRequest,
    TriggerReturnSmsResponse,
)

# Tracking Models
from .models import (
    OrderTrackingRequest,
    OrderTrackingResponse,
    OrderHistoryRequest,
    HistoryEvent,
    OrderHistoryItem,
    OrderHistoryResponse,
    TrackShipmentRequest,
    ShipmentTrackingEvent,
    ShipmentTrackingItem,
    TrackShipmentResponse,
    PrintAWBResponse,
)

# Carrier/Delivery Models
from .models import (
    CheckOTODeliveryFeeRequest,
    DeliveryOption,
    CheckDeliveryFeeResponse,
    CheckDeliveryFeeRequest,
    GetDeliveryFeeRequest,
    GetDeliveryEstimationRequest,
    CheckCoverageRequest,
    AvailableCitiesRequest,
    AvailableTimeSlotsRequest,
    GetCitiesRequest,
)

# Pickup Location Models
from .models import (
    CreatePickupLocationRequest,
    CreatePickupLocationResponse,
    UpdatePickupLocationRequest,
    UpdatePickupLocationResponse,
    PickupLocation,
    GetPickupLocationListResponse,
)

# Brand Models
from .models import (
    Brand,
    GetBrandListResponse,
    StoreConfig,
    CreateBrandRequest,
    CreateBrandResponse,
)

# Product Models
from .models import (
    CustomAttribute,
    CreateProductRequest,
    CreateProductResponse,
    Product,
    ProductListRequest,
    ProductListResponse,
)

# Box Models
from .models import (
    AddBoxRequest,
    AddBoxResponse,
    UpdateBoxRequest,
    Box,
    GetBoxResponse,
)

# Webhook Models
from .models import (
    WebhookRequest,
    WebhookResponse,
)

# Stock Models
from .models import (
    UpdateStockQuantityRequest,
    UpdateStockQuantityResponse,
)

# Generic Models
from .models import (
    SuccessResponse,
    ErrorResponse,
)

__all__ = [
    # Version
    "__version__",
    
    # Client
    "OTOAsyncClient",
    "create_client",
    
    # Exceptions
    "OTOException",
    "OTOAuthenticationError",
    "OTOAuthorizationError",
    "OTONotFoundError",
    "OTOValidationError",
    "OTOConflictError",
    "OTORateLimitError",
    "OTOServerError",
    "OTOInsufficientCreditError",
    "OTONetworkError",
    
    # Enums
    "PaymentMethod",
    "PickingType",
    "WhoPays",
    "ServiceType",
    "DeliveryType",
    "OrderStatus",
    "PickupLocationType",
    "PickupLocationStatus",
    "OnHoldReasonLang",
    
    # Core Models
    "OTOBaseModel",
    "Customer",
    "OrderItem",
    "SenderInformation",
    
    # Authentication Models
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "HealthCheckResponse",
    
    # Account Models
    "AccountInfoResponse",
    "BuyCreditRequest",
    "BuyCreditResponse",
    "CreditTransaction",
    "CreditTransactionsResponse",
    
    # Marketplace Models
    "RegisterRequest",
    "RegisterResponse",
    "ClientInfoRequest",
    "ClientInfoResponse",
    
    # Order Models
    "CreateOrderRequest",
    "CreateOrderResponse",
    "UpdateOrderRequest",
    "UpdateOrderResponse",
    "UpdateOrderStatusRequest",
    "CancelOrderRequest",
    "HoldOrderRequest",
    "UnholdOrderRequest",
    "StatusHistoryEntry",
    "OrderDetailsResponse",
    "Order",
    "GetOrdersResponse",
    "CheckOrderAvailabilityRequest",
    "LocationCoordinates",
    "AvailableLocation",
    "CheckOrderAvailabilityResponse",
    
    # Shipment Models
    "CreateShipmentRequest",
    "CreateShipmentResponse",
    "CancelShipmentRequest",
    "ShipmentTransaction",
    "ShipmentTransactionsResponse",
    "GetShippingPriceTransactionsRequest",
    "ShippingPriceTransaction",
    "GetShippingPriceTransactionsResponse",
    
    # Return Shipment Models
    "ReturnItem",
    "CreateReturnShipmentRequest",
    "CreateReturnShipmentResponse",
    "GetReturnLinkRequest",
    "GetReturnLinkResponse",
    "GetReturnDetailsRequest",
    "ReturnItemDetail",
    "GetReturnDetailsResponse",
    "TriggerReturnSmsRequest",
    "TriggerReturnSmsResponse",
    
    # Tracking Models
    "OrderTrackingRequest",
    "OrderTrackingResponse",
    "OrderHistoryRequest",
    "HistoryEvent",
    "OrderHistoryItem",
    "OrderHistoryResponse",
    "TrackShipmentRequest",
    "ShipmentTrackingEvent",
    "ShipmentTrackingItem",
    "TrackShipmentResponse",
    "PrintAWBResponse",
    
    # Carrier/Delivery Models
    "CheckOTODeliveryFeeRequest",
    "DeliveryOption",
    "CheckDeliveryFeeResponse",
    "CheckDeliveryFeeRequest",
    "GetDeliveryFeeRequest",
    "GetDeliveryEstimationRequest",
    "CheckCoverageRequest",
    "AvailableCitiesRequest",
    "AvailableTimeSlotsRequest",
    "GetCitiesRequest",
    
    # Pickup Location Models
    "CreatePickupLocationRequest",
    "CreatePickupLocationResponse",
    "UpdatePickupLocationRequest",
    "UpdatePickupLocationResponse",
    "PickupLocation",
    "GetPickupLocationListResponse",
    
    # Brand Models
    "Brand",
    "GetBrandListResponse",
    "StoreConfig",
    "CreateBrandRequest",
    "CreateBrandResponse",
    
    # Product Models
    "CustomAttribute",
    "CreateProductRequest",
    "CreateProductResponse",
    "Product",
    "ProductListRequest",
    "ProductListResponse",
    
    # Box Models
    "AddBoxRequest",
    "AddBoxResponse",
    "UpdateBoxRequest",
    "Box",
    "GetBoxResponse",
    
    # Webhook Models
    "WebhookRequest",
    "WebhookResponse",
    
    # Stock Models
    "UpdateStockQuantityRequest",
    "UpdateStockQuantityResponse",
    
    # Generic Models
    "SuccessResponse",
    "ErrorResponse",
]
