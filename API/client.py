"""
Async HTTP client for the OTO API V2.

This module provides a fully typed, async client for interacting with the OTO
logistics and fulfillment API. The client uses httpx for HTTP requests and
Pydantic models for request/response validation.

Example usage:
    >>> async with OTOAsyncClient(refresh_token="your_token") as client:
    ...     orders = await client.get_orders(status="delivered")
    ...     print(orders.orders)

The client handles automatic token refresh and provides comprehensive error
handling through custom exception classes.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import AsyncIterator, Optional, List, Dict, Any

import httpx

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
from .models import (
    # Authentication
    RefreshTokenRequest,
    RefreshTokenResponse,
    HealthCheckResponse,
    # Account
    AccountInfoResponse,
    BuyCreditRequest,
    BuyCreditResponse,
    CreditTransactionsResponse,
    # Marketplace
    RegisterRequest,
    RegisterResponse,
    ClientInfoRequest,
    ClientInfoResponse,
    # Orders
    CreateOrderRequest,
    CreateOrderResponse,
    UpdateOrderRequest,
    UpdateOrderResponse,
    UpdateOrderStatusRequest,
    CancelOrderRequest,
    HoldOrderRequest,
    UnholdOrderRequest,
    OrderDetailsResponse,
    GetOrdersResponse,
    CheckOrderAvailabilityRequest,
    CheckOrderAvailabilityResponse,
    # Shipments
    CreateShipmentRequest,
    CreateShipmentResponse,
    CancelShipmentRequest,
    ShipmentTransactionsResponse,
    GetShippingPriceTransactionsRequest,
    GetShippingPriceTransactionsResponse,
    # Returns
    CreateReturnShipmentRequest,
    CreateReturnShipmentResponse,
    GetReturnLinkRequest,
    GetReturnLinkResponse,
    GetReturnDetailsRequest,
    GetReturnDetailsResponse,
    TriggerReturnSmsRequest,
    TriggerReturnSmsResponse,
    # Tracking
    OrderTrackingRequest,
    OrderTrackingResponse,
    OrderHistoryRequest,
    OrderHistoryResponse,
    TrackShipmentRequest,
    TrackShipmentResponse,
    PrintAWBResponse,
    # Carrier/Delivery
    CheckOTODeliveryFeeRequest,
    CheckDeliveryFeeResponse,
    CheckDeliveryFeeRequest,
    GetDeliveryFeeRequest,
    GetDeliveryEstimationRequest,
    CheckCoverageRequest,
    AvailableCitiesRequest,
    AvailableTimeSlotsRequest,
    GetCitiesRequest,
    # Pickup Locations
    CreatePickupLocationRequest,
    CreatePickupLocationResponse,
    UpdatePickupLocationRequest,
    UpdatePickupLocationResponse,
    GetPickupLocationListResponse,
    # Brands
    GetBrandListResponse,
    CreateBrandRequest,
    CreateBrandResponse,
    # Products
    CreateProductRequest,
    CreateProductResponse,
    ProductListRequest,
    ProductListResponse,
    # Boxes
    AddBoxRequest,
    AddBoxResponse,
    UpdateBoxRequest,
    GetBoxResponse,
    # Stock
    UpdateStockQuantityRequest,
    UpdateStockQuantityResponse,
    # Generic
    SuccessResponse,
    ErrorResponse,
)


class OTOAsyncClient:
    """Asynchronous client for the OTO API V2.
    
    This client provides methods for all OTO API endpoints with full type safety
    and automatic token management. It uses httpx for async HTTP requests and
    validates all requests/responses using Pydantic models.
    
    Args:
        refresh_token: The permanent refresh token obtained from the OTO dashboard.
            Required for authentication with the API.
        base_url: The base URL for the OTO API. Defaults to production.
        timeout: Request timeout in seconds. Defaults to 30.
        auto_refresh: Whether to automatically refresh expired access tokens.
            Defaults to True.
    
    Attributes:
        refresh_token: The permanent refresh token.
        base_url: The API base URL.
        access_token: The current short-lived access token.
        token_expires_at: When the current access token expires.
    
    Example:
        >>> async with OTOAsyncClient(refresh_token="your_token") as client:
        ...     # Create an order
        ...     order = await client.create_order(
        ...         order_id="ORD-001",
        ...         payment_method="cod",
        ...         amount=100.0,
        ...         amount_due=100.0,
        ...         currency="SAR",
        ...         customer=Customer(name="John", mobile="+966500000000",
        ...                          address="123 Main St", city="Riyadh",
        ...                          country="SA"),
        ...         items=[OrderItem(name="Widget", sku="SKU001",
        ...                         price=100.0, quantity=1)]
        ...     )
        ...     print(f"Created order with OTO ID: {order.oto_id}")
    
    Raises:
        OTOAuthenticationError: When authentication fails or tokens are invalid.
        OTONetworkError: When network connectivity issues occur.
    """
    
    # Base URLs for different environments
    PRODUCTION_URL = "https://api.tryoto.com/rest/v2"
    STAGING_URL = "https://staging-api.tryoto.com/rest/v2"
    
    def __init__(
        self,
        refresh_token: str,
        base_url: str = PRODUCTION_URL,
        timeout: float = 30.0,
        auto_refresh: bool = True,
    ) -> None:
        """Initialize the OTO API client.
        
        Args:
            refresh_token: Permanent refresh token from OTO dashboard.
            base_url: API base URL (production or staging).
            timeout: Request timeout in seconds.
            auto_refresh: Whether to automatically refresh expired tokens.
        """
        self.refresh_token = refresh_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auto_refresh = auto_refresh
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    @property
    def access_token(self) -> Optional[str]:
        """Get the current access token."""
        return self._access_token
    
    @property
    def token_expires_at(self) -> Optional[datetime]:
        """Get the token expiration time."""
        return self._token_expires_at
    
    @property
    def is_token_expired(self) -> bool:
        """Check if the current access token is expired.
        
        Returns:
            True if the token is expired or not set, False otherwise.
        """
        if self._access_token is None or self._token_expires_at is None:
            return True
        # Add 60 second buffer to avoid edge cases
        return datetime.utcnow() >= (self._token_expires_at - timedelta(seconds=60))
    
    async def __aenter__(self) -> OTOAsyncClient:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        # Authenticate on entry
        await self._refresh_access_token()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests.
        
        Returns:
            Dictionary of HTTP headers including authorization.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers
    
    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise appropriate exception based on HTTP status code.
        
        Args:
            response: The HTTP response to check.
        
        Raises:
            OTOAuthenticationError: For 401 status.
            OTOAuthorizationError: For 403 status.
            OTONotFoundError: For 404 status.
            OTOValidationError: For 400 status.
            OTOConflictError: For 409 status.
            OTORateLimitError: For 429 status.
            OTOServerError: For 5xx status.
            OTOException: For other error status codes.
        """
        if response.is_success:
            return
        
        status = response.status_code
        try:
            data = response.json()
            error_code = data.get("otoErrorCode", "")
            error_message = data.get("otoErrorMessage", response.text)
        except Exception:
            error_code = ""
            error_message = response.text
        
        # Check for insufficient credit error
        if "insufficient" in error_message.lower() and "credit" in error_message.lower():
            raise OTOInsufficientCreditError(
                message="Insufficient credit balance",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        
        if status == 400:
            raise OTOValidationError(
                message="Validation error",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status == 401:
            raise OTOAuthenticationError(
                message="Authentication failed",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status == 403:
            raise OTOAuthorizationError(
                message="Authorization denied",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status == 404:
            raise OTONotFoundError(
                message="Resource not found",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status == 409:
            raise OTOConflictError(
                message="Resource conflict",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status == 429:
            raise OTORateLimitError(
                message="Rate limit exceeded",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        elif status >= 500:
            raise OTOServerError(
                message="Server error",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
        else:
            raise OTOException(
                message=f"HTTP error {status}",
                status_code=status,
                error_code=error_code,
                error_message=error_message,
            )
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized.
        
        Returns:
            The initialized httpx AsyncClient.
        
        Raises:
            RuntimeError: If client is used outside context manager.
        """
        if self._client is None:
            raise RuntimeError(
                "Client not initialized. Use 'async with OTOAsyncClient(...) as client:'"
            )
        return self._client
    
    async def _ensure_authenticated(self) -> None:
        """Ensure a valid access token is available.
        
        Refreshes the token if expired and auto_refresh is enabled.
        
        Raises:
            OTOAuthenticationError: If token refresh fails.
        """
        if self.auto_refresh and self.is_token_expired:
            await self._refresh_access_token()
    
    async def _refresh_access_token(self) -> RefreshTokenResponse:
        """Refresh the access token using the refresh token.
        
        This method is thread-safe and uses a lock to prevent concurrent
        refresh attempts.
        
        Returns:
            RefreshTokenResponse containing the new tokens.
        
        Raises:
            OTOAuthenticationError: If token refresh fails.
            OTONetworkError: If a network error occurs.
        """
        async with self._lock:
            # Double-check after acquiring lock
            if not self.is_token_expired:
                return RefreshTokenResponse(
                    access_token=self._access_token or "",
                    refresh_token=self.refresh_token,
                    success=True,
                    expires_in="3600",
                )
            
            client = await self._ensure_client()
            
            try:
                response = await client.post(
                    "/refreshToken",
                    json={"refresh_token": self.refresh_token},
                    headers={"Content-Type": "application/json"},
                )
            except httpx.RequestError as e:
                raise OTONetworkError(
                    message=f"Network error during token refresh: {e}",
                    original_error=e,
                )
            
            self._raise_for_status(response)
            
            data = response.json()
            result = RefreshTokenResponse.model_validate(data)
            
            self._access_token = result.access_token
            # Parse expires_in (e.g., "3600" or "1h")
            try:
                expires_seconds = int(result.expires_in.rstrip("s").rstrip("h"))
                if "h" in result.expires_in:
                    expires_seconds *= 3600
            except ValueError:
                expires_seconds = 3600  # Default to 1 hour
            
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_seconds)
            
            return result
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated HTTP request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            params: Query parameters.
            json_data: JSON body data.
        
        Returns:
            Parsed JSON response as a dictionary.
        
        Raises:
            OTOException: For API errors.
            OTONetworkError: For network errors.
        """
        await self._ensure_authenticated()
        client = await self._ensure_client()
        
        # Remove None values from params
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        
        # Remove None values from json_data
        if json_data:
            json_data = {k: v for k, v in json_data.items() if v is not None}
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=self._get_headers(),
            )
        except httpx.RequestError as e:
            raise OTONetworkError(
                message=f"Network error: {e}",
                original_error=e,
            )
        
        self._raise_for_status(response)
        
        return response.json()
    
    # =========================================================================
    # AUTHORIZATION ENDPOINTS
    # =========================================================================
    
    async def refresh_token(self) -> RefreshTokenResponse:
        """Manually refresh the access token.
        
        Call this method to explicitly refresh the access token. Note that
        if auto_refresh is enabled (default), the client will automatically
        refresh expired tokens before each request.
        
        Returns:
            RefreshTokenResponse: Contains the new access_token, refresh_token,
                token_type, and expires_in fields.
        
        Raises:
            OTOAuthenticationError: If the refresh token is invalid or expired.
            OTONetworkError: If a network error occurs during the request.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     tokens = await client.refresh_token()
            ...     print(f"New token expires in: {tokens.expires_in}")
        """
        return await self._refresh_access_token()
    
    async def health_check(self) -> HealthCheckResponse:
        """Check the health status of the OTO API.
        
        Use this endpoint to verify that the API is operational and your
        authentication is valid.
        
        Returns:
            HealthCheckResponse: Contains the status field (typically "ok").
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     health = await client.health_check()
            ...     assert health.status == "ok"
        """
        data = await self._request("GET", "/healthCheck")
        return HealthCheckResponse.model_validate(data)
    
    # =========================================================================
    # ACCOUNT ENDPOINTS
    # =========================================================================
    
    async def get_account_info(self) -> AccountInfoResponse:
        """Get account information including credit balance.
        
        Retrieves the current account details including name, email, mobile,
        subscription package, and remaining credit balance.
        
        Returns:
            AccountInfoResponse: Contains account details including:
                - name: Account owner name
                - email: Account email
                - mobile: Account mobile number
                - package_name: Current subscription package
                - remaining_credit: Available credit balance
                - remaining_free_shipments: Free shipments from campaigns
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     info = await client.get_account_info()
            ...     print(f"Credit balance: {info.remaining_credit}")
        """
        data = await self._request("GET", "/accountInfo")
        return AccountInfoResponse.model_validate(data)
    
    async def buy_credit(self, amount: float) -> BuyCreditResponse:
        """Initiate a credit purchase for the account.
        
        Creates a payment session for purchasing account credit. Returns a
        payment URL where the user can complete the transaction.
        
        Args:
            amount: The amount of credit to purchase in the account currency.
                Must be greater than 0.
        
        Returns:
            BuyCreditResponse: Contains:
                - success: Whether the request was successful
                - payment_url: URL to complete the payment
                - payment_id: Unique payment transaction identifier
        
        Raises:
            OTOValidationError: If the amount is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.buy_credit(amount=100.0)
            ...     print(f"Complete payment at: {result.payment_url}")
        """
        request = BuyCreditRequest(amount=amount)
        data = await self._request(
            "POST",
            "/buyCredit",
            json_data=request.model_dump(by_alias=True),
        )
        return BuyCreditResponse.model_validate(data)
    
    async def get_credit_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> CreditTransactionsResponse:
        """Get the list of credit transactions for the account.
        
        Retrieves the history of credit transactions including charges,
        refunds, and other financial operations.
        
        Args:
            from_date: Start date filter in YYYY-MM-DD format. Optional.
            to_date: End date filter in YYYY-MM-DD format. Optional.
        
        Returns:
            CreditTransactionsResponse: Contains:
                - success: Whether the request was successful
                - transactions: List of CreditTransaction objects
        
        Raises:
            OTOValidationError: If date format is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     txns = await client.get_credit_transactions(
            ...         from_date="2024-01-01",
            ...         to_date="2024-01-31"
            ...     )
            ...     for txn in txns.transactions:
            ...         print(f"{txn.transaction_date}: {txn.amount}")
        """
        data = await self._request(
            "GET",
            "/creditTransactions",
            params={"fromDate": from_date, "toDate": to_date},
        )
        return CreditTransactionsResponse.model_validate(data)
    
    # =========================================================================
    # MARKETPLACE ENDPOINTS
    # =========================================================================
    
    async def register_vendor(self, request: RegisterRequest) -> RegisterResponse:
        """Register a new vendor account (marketplace use only).
        
        This endpoint is only available for marketplace accounts. It creates
        a new vendor/seller account under the marketplace.
        
        Args:
            request: RegisterRequest containing vendor details:
                - company_name: Vendor's company name (required)
                - email: Vendor's email address (required)
                - full_name: Contact person's name (required)
                - mobile_number: Contact phone number (required)
                - Additional optional fields for billing, webhook, etc.
        
        Returns:
            RegisterResponse: Contains:
                - success: Whether registration was successful
                - activation_link: URL for the vendor to activate their account
                - refresh_token: API refresh token for the new vendor
        
        Raises:
            OTOValidationError: If required fields are missing or invalid.
            OTOAuthorizationError: If not a marketplace account.
            OTOConflictError: If email already registered.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="marketplace_token") as client:
            ...     result = await client.register_vendor(RegisterRequest(
            ...         company_name="Acme Corp",
            ...         email="vendor@acme.com",
            ...         full_name="John Smith",
            ...         mobile_number="+966500000000"
            ...     ))
            ...     print(f"Activation link: {result.activation_link}")
        """
        data = await self._request(
            "POST",
            "/register",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return RegisterResponse.model_validate(data)
    
    async def get_client_info(self, email: str) -> ClientInfoResponse:
        """Get client/vendor information by email (marketplace use only).
        
        Retrieves account information for a vendor under the marketplace
        using their registered email address.
        
        Args:
            email: The registered email address of the client/vendor.
        
        Returns:
            ClientInfoResponse: Contains:
                - success: Whether the request was successful
                - remaining_credit: Available credit balance
                - validity_date: Account validity/expiration date
                - user_activated: Whether the user has activated their account
                - refresh_token: API refresh token for the client
                - name: Client/company name
                - email: Registered email
                - phone: Contact phone number
        
        Raises:
            OTONotFoundError: If no client found with the given email.
            OTOAuthorizationError: If not a marketplace account.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="marketplace_token") as client:
            ...     info = await client.get_client_info("vendor@acme.com")
            ...     print(f"Vendor credit: {info.remaining_credit}")
        """
        request = ClientInfoRequest(email=email)
        data = await self._request(
            "POST",
            "/clientInfo",
            json_data=request.model_dump(by_alias=True),
        )
        return ClientInfoResponse.model_validate(data)
    
    # =========================================================================
    # ORDER ENDPOINTS
    # =========================================================================
    
    async def create_order(self, request: CreateOrderRequest) -> CreateOrderResponse:
        """Create a new order in OTO.
        
        Creates a new order with the specified details. The order can optionally
        have a shipment created automatically by setting create_shipment=True.
        
        Args:
            request: CreateOrderRequest containing:
                - order_id: Your unique order identifier (required)
                - payment_method: "cod" or "paid" (required)
                - amount: Total order value (required)
                - amount_due: Amount due from customer (required)
                - currency: ISO 4217 currency code (required)
                - customer: Customer details including address (required)
                - items: List of order items (required)
                - Many optional fields for shipping preferences, etc.
        
        Returns:
            CreateOrderResponse: Contains:
                - success: Whether order creation was successful
                - oto_id: Internal OTO identifier for the order
        
        Raises:
            OTOValidationError: If required fields are missing or invalid.
            OTOConflictError: If order_id already exists.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> from oto_api.models import Customer, OrderItem
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     order = await client.create_order(CreateOrderRequest(
            ...         order_id="ORD-12345",
            ...         payment_method="cod",
            ...         amount=150.0,
            ...         amount_due=150.0,
            ...         currency="SAR",
            ...         customer=Customer(
            ...             name="Ahmed Mohammed",
            ...             mobile="+966500000000",
            ...             address="123 King Fahd Road",
            ...             city="Riyadh",
            ...             country="SA"
            ...         ),
            ...         items=[OrderItem(
            ...             name="Widget",
            ...             sku="WDG-001",
            ...             price=150.0,
            ...             quantity=1
            ...         )]
            ...     ))
            ...     print(f"Created order with OTO ID: {order.oto_id}")
        """
        data = await self._request(
            "POST",
            "/createOrder",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreateOrderResponse.model_validate(data)
    
    async def update_order(self, request: UpdateOrderRequest) -> UpdateOrderResponse:
        """Update an existing order.
        
        Updates order details. Note that orders can only be updated before
        a shipment is created. If a shipment exists, cancel it first.
        
        Args:
            request: UpdateOrderRequest containing:
                - order_id: The order ID to update (required)
                - Any fields to update (all optional)
        
        Returns:
            UpdateOrderResponse: Contains:
                - success: Whether the update was successful
                - message: Status or error message
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOValidationError: If the update data is invalid.
            OTOConflictError: If a shipment exists for the order.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.update_order(UpdateOrderRequest(
            ...         order_id="ORD-12345",
            ...         shipping_notes="Please call before delivery"
            ...     ))
            ...     print(f"Update successful: {result.success}")
        """
        data = await self._request(
            "POST",
            "/updateOrder",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return UpdateOrderResponse.model_validate(data)
    
    async def update_order_status(
        self,
        request: UpdateOrderStatusRequest,
    ) -> SuccessResponse:
        """Update the status of one or more orders.
        
        Allows updating orders to delivered, returned, or pickedUp status
        for bulk status management.
        
        Args:
            request: UpdateOrderStatusRequest containing:
                - order_ids: List of order IDs to update (required)
                - status: New status (delivered, returned, pickedUp) (required)
                - description: Optional status change description
                - date: Optional delivery/update date
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If any order does not exist.
            OTOValidationError: If the status is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.update_order_status(
            ...         UpdateOrderStatusRequest(
            ...             order_ids=["ORD-001", "ORD-002"],
            ...             status="delivered",
            ...             date="2024-01-15"
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/updateOrderStatus",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def cancel_order(self, order_id: str) -> SuccessResponse:
        """Cancel an order.
        
        Cancels an order that does not have an associated shipment.
        Orders with shipments cannot be canceled through this endpoint.
        
        Args:
            order_id: The order ID to cancel.
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOConflictError: If the order has an active shipment.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.cancel_order("ORD-12345")
            ...     print(f"Order canceled: {result.success}")
        """
        request = CancelOrderRequest(order_id=order_id)
        data = await self._request(
            "POST",
            "/cancelOrder",
            json_data=request.model_dump(by_alias=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def get_orders(
        self,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
        payment_method: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_name: Optional[str] = None,
        destination_city: Optional[str] = None,
        origin_city: Optional[str] = None,
        order_id: Optional[str] = None,
        delivery_company: Optional[str] = None,
        brand_id: Optional[int] = None,
        entity_id: Optional[int] = None,
        parent_order_id: Optional[str] = None,
        shipment_id: Optional[str] = None,
    ) -> GetOrdersResponse:
        """Get a list of orders with optional filters.
        
        Retrieves orders matching the specified criteria. Supports pagination
        and various filter options.
        
        Args:
            status: Filter by order status (e.g., "delivered", "shipped").
            from_date: Filter orders created on or after this date (YYYY-MM-DD).
            to_date: Filter orders created on or before this date (YYYY-MM-DD).
            per_page: Number of orders per page (default varies by account).
            page: Page number for pagination (1-indexed).
            payment_method: Filter by payment method ("cod" or "paid").
            customer_phone: Filter by customer phone number.
            customer_name: Filter by customer name (partial match).
            destination_city: Filter by delivery city.
            origin_city: Filter by pickup city.
            order_id: Filter by specific order ID.
            delivery_company: Filter by delivery company code.
            brand_id: Filter by brand ID.
            entity_id: Filter by sales channel entity ID.
            parent_order_id: Filter by parent order ID (for split orders).
            shipment_id: Filter by shipment ID.
        
        Returns:
            GetOrdersResponse: Contains:
                - success: Whether the request was successful
                - orders: List of Order objects
                - per_page: Number of orders per page
                - current_page: Current page number
                - total_page: Total number of pages
                - total_count: Total number of matching orders
        
        Raises:
            OTOValidationError: If filter parameters are invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     # Get delivered orders from January
            ...     orders = await client.get_orders(
            ...         status="delivered",
            ...         from_date="2024-01-01",
            ...         to_date="2024-01-31",
            ...         per_page=50
            ...     )
            ...     for order in orders.orders:
            ...         print(f"{order.order_id}: {order.status}")
        """
        data = await self._request(
            "GET",
            "/orders",
            params={
                "status": status,
                "fromDate": from_date,
                "toDate": to_date,
                "perPage": per_page,
                "page": page,
                "paymentMethod": payment_method,
                "customerPhone": customer_phone,
                "customerName": customer_name,
                "destinationCity": destination_city,
                "originCity": origin_city,
                "orderId": order_id,
                "deliveryCompany": delivery_company,
                "brandId": brand_id,
                "entityId": entity_id,
                "parentOrderId": parent_order_id,
                "shipmentId": shipment_id,
            },
        )
        return GetOrdersResponse.model_validate(data)
    
    async def hold_order(
        self,
        order_id: str,
        on_hold_reason: str,
        on_hold_reason_lang: str = "en",
    ) -> SuccessResponse:
        """Place an order on hold.
        
        Temporarily pauses order processing. The hold reason is shown to
        the customer in the tracking page.
        
        Args:
            order_id: The order ID to place on hold.
            on_hold_reason: Reason for placing the order on hold.
            on_hold_reason_lang: Language code for the reason (en, tr, ar).
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOValidationError: If the language code is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.hold_order(
            ...         order_id="ORD-12345",
            ...         on_hold_reason="Awaiting customer confirmation",
            ...         on_hold_reason_lang="en"
            ...     )
        """
        request = HoldOrderRequest(
            order_id=order_id,
            on_hold_reason=on_hold_reason,
            on_hold_reason_lang=on_hold_reason_lang,
        )
        data = await self._request(
            "POST",
            "/holdOrder",
            json_data=request.model_dump(by_alias=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def unhold_order(self, order_id: str) -> SuccessResponse:
        """Release an order from hold.
        
        Resumes processing for an order that was previously placed on hold.
        
        Args:
            order_id: The order ID to release from hold.
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOValidationError: If the order is not on hold.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.unhold_order("ORD-12345")
            ...     print(f"Order released: {result.success}")
        """
        request = UnholdOrderRequest(order_id=order_id)
        data = await self._request(
            "POST",
            "/unholdOrder",
            json_data=request.model_dump(by_alias=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def get_order_details(self, order_id: str) -> OrderDetailsResponse:
        """Get detailed information about a specific order.
        
        Retrieves comprehensive details about an order including items,
        status history, tracking information, and delivery details.
        
        Args:
            order_id: The order ID to retrieve details for.
        
        Returns:
            OrderDetailsResponse: Contains comprehensive order details including:
                - order_id: The order identifier
                - status: Current order status
                - items: List of items in the order
                - status_history: History of status changes
                - tracking_url: URL for tracking the shipment
                - And many more fields...
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     details = await client.get_order_details("ORD-12345")
            ...     print(f"Status: {details.status}")
            ...     print(f"Tracking: {details.tracking_url}")
        """
        data = await self._request(
            "GET",
            "/orderDetails",
            params={"orderId": order_id},
        )
        return OrderDetailsResponse.model_validate(data)
    
    async def check_order_availability(
        self,
        request: CheckOrderAvailabilityRequest,
    ) -> CheckOrderAvailabilityResponse:
        """Check order availability across fulfillment locations.
        
        Checks if an order can be fulfilled and from which locations
        based on inventory availability rules.
        
        Args:
            request: CheckOrderAvailabilityRequest containing:
                - order_id: Order ID to check availability for (required)
                - rule_ids: Optional list of OMS rule IDs to use
        
        Returns:
            CheckOrderAvailabilityResponse: Contains:
                - success: Whether the check was successful
                - order_availability: Availability status string
                - locations: List of locations where order can be fulfilled
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     avail = await client.check_order_availability(
            ...         CheckOrderAvailabilityRequest(order_id="ORD-12345")
            ...     )
            ...     for loc in avail.locations:
            ...         print(f"{loc.location_name}: {loc.distance}km")
        """
        data = await self._request(
            "POST",
            "/checkOrderAvailability",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CheckOrderAvailabilityResponse.model_validate(data)
    
    # =========================================================================
    # SHIPMENT ENDPOINTS
    # =========================================================================
    
    async def create_shipment(
        self,
        request: CreateShipmentRequest,
    ) -> CreateShipmentResponse:
        """Create a shipment for an existing order.
        
        Creates a shipment with the specified delivery company option.
        The order must exist and not already have an active shipment.
        
        Args:
            request: CreateShipmentRequest containing:
                - order_id: The order ID to create a shipment for (required)
                - delivery_option_id: Specific delivery option ID (optional)
                - picking_type: PICKUP_BY_DC or BRANCH_DROP_OFF (optional)
                - who_pays: Who pays for the shipment (optional)
                - ID card images for international shipments (optional)
        
        Returns:
            CreateShipmentResponse: Contains:
                - success: Whether shipment creation was successful
                - message: Status message
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOConflictError: If a shipment already exists.
            OTOInsufficientCreditError: If credit balance is insufficient.
            OTOValidationError: If request data is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.create_shipment(
            ...         CreateShipmentRequest(order_id="ORD-12345")
            ...     )
            ...     print(f"Shipment created: {result.success}")
        """
        data = await self._request(
            "POST",
            "/createShipment",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreateShipmentResponse.model_validate(data)
    
    async def cancel_shipment(
        self,
        order_id: str,
        shipment_id: str,
    ) -> SuccessResponse:
        """Cancel a shipment.
        
        Cancels an existing shipment. Shipments cannot be canceled after
        the package has been picked up.
        
        Args:
            order_id: The order ID associated with the shipment.
            shipment_id: The shipment ID to cancel.
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If the order or shipment does not exist.
            OTOConflictError: If the shipment has already been picked up.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.cancel_shipment(
            ...         order_id="ORD-12345",
            ...         shipment_id="SHIP-67890"
            ...     )
            ...     print(f"Shipment canceled: {result.success}")
        """
        request = CancelShipmentRequest(order_id=order_id, shipment_id=shipment_id)
        data = await self._request(
            "POST",
            "/cancelShipment",
            json_data=request.model_dump(by_alias=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def get_shipment_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> ShipmentTransactionsResponse:
        """Get the list of shipment transactions.
        
        Retrieves shipment transaction records including delivery charges
        and weight adjustments.
        
        Args:
            from_date: Start date filter (YYYY-MM-DD).
            to_date: End date filter (YYYY-MM-DD).
            page: Page number for pagination.
            per_page: Number of records per page.
        
        Returns:
            ShipmentTransactionsResponse: Contains:
                - success: Whether the request was successful
                - shipments: List of ShipmentTransaction objects
        
        Raises:
            OTOValidationError: If date format is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     txns = await client.get_shipment_transactions(
            ...         from_date="2024-01-01"
            ...     )
            ...     for txn in txns.shipments:
            ...         print(f"{txn.shipment_number}: {txn.dc_charge}")
        """
        data = await self._request(
            "GET",
            "/shipmentTransactions",
            params={
                "fromDate": from_date,
                "toDate": to_date,
                "page": page,
                "perPage": per_page,
            },
        )
        return ShipmentTransactionsResponse.model_validate(data)
    
    async def get_shipping_price_transactions(
        self,
        order_id: Optional[str] = None,
        shipment_id: Optional[str] = None,
    ) -> GetShippingPriceTransactionsResponse:
        """Get shipping price transactions for an order or shipment.
        
        Retrieves the detailed breakdown of shipping charges and refunds.
        
        Args:
            order_id: Filter by order ID.
            shipment_id: Filter by shipment ID.
        
        Returns:
            GetShippingPriceTransactionsResponse: Contains:
                - success: Whether the request was successful
                - count: Number of transactions
                - shipping_transactions: List of price transactions
        
        Raises:
            OTONotFoundError: If the order or shipment does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     prices = await client.get_shipping_price_transactions(
            ...         order_id="ORD-12345"
            ...     )
            ...     for txn in prices.shipping_transactions:
            ...         print(f"{txn.description}: {txn.amount}")
        """
        data = await self._request(
            "GET",
            "/getShippingPriceTransactionsList",
            params={"orderId": order_id, "shipmentId": shipment_id},
        )
        return GetShippingPriceTransactionsResponse.model_validate(data)
    
    # =========================================================================
    # RETURN SHIPMENT ENDPOINTS
    # =========================================================================
    
    async def create_return_shipment(
        self,
        request: CreateReturnShipmentRequest,
    ) -> CreateReturnShipmentResponse:
        """Create a return/reverse shipment for a delivered order.
        
        Creates a return shipment to pick up items from the customer
        and return them to the specified location.
        
        Args:
            request: CreateReturnShipmentRequest containing:
                - order_id: The delivered order ID (required)
                - delivery_option_id: Specific delivery option (optional)
                - pickup_location_code: Return destination location (optional)
                - picking_type: PICKUP_BY_DC or BRANCH_DROP_OFF (optional)
                - items: List of items being returned (optional)
        
        Returns:
            CreateReturnShipmentResponse: Contains:
                - success: Whether the return was created
                - msg: Status message
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOValidationError: If order is not in delivered status.
            OTOInsufficientCreditError: If credit balance is insufficient.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.create_return_shipment(
            ...         CreateReturnShipmentRequest(order_id="ORD-12345")
            ...     )
            ...     print(f"Return created: {result.success}")
        """
        data = await self._request(
            "POST",
            "/createReturnShipment",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreateReturnShipmentResponse.model_validate(data)
    
    async def get_return_link(self, order_id: str) -> GetReturnLinkResponse:
        """Get the customer return portal link for an order.
        
        Generates a link that can be shared with the customer to initiate
        a return through the self-service portal.
        
        Args:
            order_id: The order ID to generate a return link for.
        
        Returns:
            GetReturnLinkResponse: Contains:
                - success: Whether the link was generated
                - return_link: URL for the customer return portal
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.get_return_link("ORD-12345")
            ...     print(f"Return portal: {result.return_link}")
        """
        request = GetReturnLinkRequest(order_id=order_id)
        data = await self._request(
            "POST",
            "/getReturnLink",
            json_data=request.model_dump(by_alias=True),
        )
        return GetReturnLinkResponse.model_validate(data)
    
    async def get_return_details(self, order_id: str) -> GetReturnDetailsResponse:
        """Get details about a return shipment.
        
        Retrieves the current status and details of a return shipment
        for the specified order.
        
        Args:
            order_id: The order ID to get return details for.
        
        Returns:
            GetReturnDetailsResponse: Contains:
                - order_id: The order identifier
                - status: Current return status
                - return_reason: Reason for the return
                - return_location_code: Destination location
                - items: List of items in the return
        
        Raises:
            OTONotFoundError: If the order or return does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     details = await client.get_return_details("ORD-12345")
            ...     print(f"Return status: {details.status}")
        """
        request = GetReturnDetailsRequest(order_id=order_id)
        data = await self._request(
            "POST",
            "/getReturnDetails",
            json_data=request.model_dump(by_alias=True),
        )
        return GetReturnDetailsResponse.model_validate(data)
    
    async def trigger_return_sms(self, order_id: str) -> TriggerReturnSmsResponse:
        """Trigger a return SMS notification to the customer.
        
        Sends an SMS to the customer with return instructions and portal link.
        
        Args:
            order_id: The order ID to send return SMS for.
        
        Returns:
            TriggerReturnSmsResponse: Contains:
                - success: Whether the SMS was triggered
                - oto_id: Internal OTO identifier
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.trigger_return_sms("ORD-12345")
            ...     print(f"SMS sent: {result.success}")
        """
        request = TriggerReturnSmsRequest(order_id=order_id)
        data = await self._request(
            "POST",
            "/triggerReturnSms",
            json_data=request.model_dump(by_alias=True),
        )
        return TriggerReturnSmsResponse.model_validate(data)
    
    # =========================================================================
    # TRACKING ENDPOINTS
    # =========================================================================
    
    async def get_order_status(self, order_id: str) -> OrderTrackingResponse:
        """Get the current tracking status of an order.
        
        Retrieves the latest status and tracking information for an order.
        
        Args:
            order_id: The order ID to get status for.
        
        Returns:
            OrderTrackingResponse: Contains:
                - order_id: The order identifier
                - status: Current order status
                - delivery_company: Carrier handling the shipment
                - shipment_id: Shipment identifier
                - dc_tracking_number: Delivery company tracking number
                - date: Last update timestamp
                - print_awb_url: URL to print the shipping label
        
        Raises:
            OTONotFoundError: If the order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     status = await client.get_order_status("ORD-12345")
            ...     print(f"Status: {status.status}")
            ...     print(f"Carrier: {status.delivery_company}")
        """
        data = await self._request(
            "GET",
            "/orderStatus",
            params={"orderId": order_id},
        )
        return OrderTrackingResponse.model_validate(data)
    
    async def get_order_history(
        self,
        order_ids: List[str],
    ) -> OrderHistoryResponse:
        """Get the status history for one or more orders.
        
        Retrieves the complete history of status changes for the specified
        orders, including timestamps, descriptions, and associated shipments.
        
        Args:
            order_ids: List of order IDs to get history for.
        
        Returns:
            OrderHistoryResponse: Contains:
                - success: Whether the request was successful
                - items: List of OrderHistoryItem objects with full history
        
        Raises:
            OTONotFoundError: If any order does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     history = await client.get_order_history(["ORD-12345"])
            ...     for item in history.items:
            ...         for event in item.history:
            ...             print(f"{event.date}: {event.status}")
        """
        request = OrderHistoryRequest(order_ids=order_ids)
        data = await self._request(
            "POST",
            "/orderHistory",
            json_data=request.model_dump(by_alias=True),
        )
        return OrderHistoryResponse.model_validate(data)
    
    async def track_shipment(
        self,
        request: TrackShipmentRequest,
    ) -> TrackShipmentResponse:
        """Track a shipment by tracking number and carrier.
        
        Retrieves tracking information directly from the delivery company
        using the shipment's tracking number.
        
        Args:
            request: TrackShipmentRequest containing:
                - tracking_number: The shipment/tracking number (required)
                - delivery_company_name: Carrier name/code (required)
                - status_history: Whether to include full history (required)
                - brand_name: Associated brand name (optional)
        
        Returns:
            TrackShipmentResponse: Contains:
                - success: Whether tracking was successful
                - tracking_url: Carrier's tracking URL
                - items: List of tracking items with status and history
        
        Raises:
            OTONotFoundError: If the tracking number is not found.
            OTOValidationError: If carrier name is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     tracking = await client.track_shipment(
            ...         TrackShipmentRequest(
            ...             tracking_number="1234567890",
            ...             delivery_company_name="aramex",
            ...             status_history=True
            ...         )
            ...     )
            ...     print(f"Tracking URL: {tracking.tracking_url}")
        """
        data = await self._request(
            "POST",
            "/trackShipment",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return TrackShipmentResponse.model_validate(data)
    
    async def print_awb(self, order_id: str) -> PrintAWBResponse:
        """Get the shipping label (AWB) for an order.
        
        Retrieves the URL to download or print the shipping label
        for an order with an active shipment.
        
        Args:
            order_id: The order ID to get the AWB for.
        
        Returns:
            PrintAWBResponse: Contains:
                - print_awb_url: URL to download/print the shipping label
                - delivery_company: Carrier for the shipment
                - tracking_number: Tracking number on the label
        
        Raises:
            OTONotFoundError: If the order or shipment does not exist.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     awb = await client.print_awb("ORD-12345")
            ...     print(f"AWB URL: {awb.print_awb_url}")
        """
        data = await self._request(
            "GET",
            "/printAWB",
            params={"orderId": order_id},
        )
        return PrintAWBResponse.model_validate(data)
    
    # =========================================================================
    # CARRIER/DELIVERY ENDPOINTS
    # =========================================================================
    
    async def check_oto_delivery_fee(
        self,
        request: CheckOTODeliveryFeeRequest,
    ) -> CheckDeliveryFeeResponse:
        """Check OTO delivery fees and available carriers.
        
        Queries available delivery options and their prices from OTO's
        carrier marketplace based on route and package details.
        
        Args:
            request: CheckOTODeliveryFeeRequest containing:
                - origin_city: Pickup city name (required)
                - destination_city: Delivery city name (required)
                - weight: Package weight in kg (required)
                - Optional: dimensions, coordinates, service type filters
        
        Returns:
            CheckDeliveryFeeResponse: Contains:
                - success: Whether the check was successful
                - delivery_company: List of available DeliveryOption objects
                - trace_id: Request trace ID for debugging
        
        Raises:
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     fees = await client.check_oto_delivery_fee(
            ...         CheckOTODeliveryFeeRequest(
            ...             origin_city="Riyadh",
            ...             destination_city="Jeddah",
            ...             weight=2.5
            ...         )
            ...     )
            ...     for option in fees.delivery_company:
            ...         print(f"{option.delivery_company_name}: {option.price}")
        """
        data = await self._request(
            "POST",
            "/checkOTODeliveryFee",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CheckDeliveryFeeResponse.model_validate(data)
    
    async def check_delivery_fee(
        self,
        request: CheckDeliveryFeeRequest,
    ) -> CheckDeliveryFeeResponse:
        """Check delivery fees for your contract carriers.
        
        Queries available delivery options and prices from carriers
        that you have direct contracts with in OTO.
        
        Args:
            request: CheckDeliveryFeeRequest containing:
                - origin_city: Pickup city name (required)
                - destination_city: Delivery city name (required)
                - weight: Package weight in kg (required)
                - Optional: dimensions, delivery type, coordinates
        
        Returns:
            CheckDeliveryFeeResponse: Contains available delivery options.
        
        Raises:
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     fees = await client.check_delivery_fee(
            ...         CheckDeliveryFeeRequest(
            ...             origin_city="Riyadh",
            ...             destination_city="Dammam",
            ...             weight=1.0
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/checkDeliveryFee",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CheckDeliveryFeeResponse.model_validate(data)
    
    async def get_delivery_fee(
        self,
        request: GetDeliveryFeeRequest,
    ) -> CheckDeliveryFeeResponse:
        """Get all available delivery fees (OTO + contract carriers).
        
        Combines results from both OTO marketplace and your contract
        carriers to show all available delivery options.
        
        Args:
            request: GetDeliveryFeeRequest containing:
                - origin_city: Pickup city name (required)
                - destination_city: Delivery city name (required)
                - weight: Package weight in kg (required)
                - Optional: dimensions, COD amount
        
        Returns:
            CheckDeliveryFeeResponse: Contains all available delivery options.
        
        Raises:
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     all_fees = await client.get_delivery_fee(
            ...         GetDeliveryFeeRequest(
            ...             origin_city="Riyadh",
            ...             destination_city="Jeddah",
            ...             weight=5.0,
            ...             total_due=500.0  # COD amount
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/getDeliveryFee",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CheckDeliveryFeeResponse.model_validate(data)
    
    async def get_delivery_estimation(
        self,
        request: GetDeliveryEstimationRequest,
    ) -> SuccessResponse:
        """Get estimated delivery time for a route and carrier.
        
        Queries the expected delivery time for a specific delivery
        option on a given route.
        
        Args:
            request: GetDeliveryEstimationRequest containing:
                - origin_city: Pickup city name (required)
                - destination_city: Delivery city name (required)
                - delivery_option_id: Specific delivery option (required)
                - district: District for district-based SLA (optional)
        
        Returns:
            SuccessResponse: Contains estimated delivery information.
        
        Raises:
            OTOValidationError: If required fields are missing.
            OTONotFoundError: If the delivery option is not found.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        """
        data = await self._request(
            "POST",
            "/getDeliveryEstimation",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def check_coverage(
        self,
        request: CheckCoverageRequest,
    ) -> SuccessResponse:
        """Check if a route is covered by available carriers.
        
        Verifies whether delivery is possible between origin and
        destination cities.
        
        Args:
            request: CheckCoverageRequest containing:
                - origin_city: Pickup city name (required)
                - destination_city: Delivery city name (required)
                - package_size: Package size category (optional)
        
        Returns:
            SuccessResponse: Contains coverage availability information.
        
        Raises:
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        """
        data = await self._request(
            "POST",
            "/checkCoverage",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def get_cities(
        self,
        country: str,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
    ) -> SuccessResponse:
        """Get the list of cities for a country.
        
        Retrieves all available cities for the specified country code.
        
        Args:
            country: ISO2 country code (e.g., "SA", "AE").
            per_page: Results per page (default 100, max 500).
            page: Page number for pagination.
        
        Returns:
            SuccessResponse: Contains list of cities.
        
        Raises:
            OTOValidationError: If country code is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     cities = await client.get_cities("SA", per_page=100)
        """
        data = await self._request(
            "GET",
            "/getCities",
            params={"country": country, "perPage": per_page, "page": page},
        )
        return SuccessResponse.model_validate(data)
    
    # =========================================================================
    # PICKUP LOCATION ENDPOINTS
    # =========================================================================
    
    async def create_pickup_location(
        self,
        request: CreatePickupLocationRequest,
    ) -> CreatePickupLocationResponse:
        """Create a new pickup location (warehouse or branch).
        
        Creates a new location from which orders can be fulfilled and
        shipped.
        
        Args:
            request: CreatePickupLocationRequest containing:
                - name: Location name (required)
                - code: Unique location code (required)
                - mobile: Contact phone number (required)
                - city: City name (required)
                - country: ISO2 country code (required)
                - address: Full address (required)
                - contact_name: Contact person's name (required)
                - contact_email: Contact person's email (required)
                - Optional: type, coordinates, postal details
        
        Returns:
            CreatePickupLocationResponse: Contains:
                - success: Whether creation was successful
                - warehouse_id: ID of the created location
                - pickup_location_code: The location code
        
        Raises:
            OTOConflictError: If the code already exists.
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     location = await client.create_pickup_location(
            ...         CreatePickupLocationRequest(
            ...             name="Main Warehouse",
            ...             code="WH-001",
            ...             mobile="+966500000000",
            ...             city="Riyadh",
            ...             country="SA",
            ...             address="Industrial Area, Building 5",
            ...             contact_name="Ahmed",
            ...             contact_email="ahmed@company.com"
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/createPickupLocation",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreatePickupLocationResponse.model_validate(data)
    
    async def update_pickup_location(
        self,
        request: UpdatePickupLocationRequest,
    ) -> UpdatePickupLocationResponse:
        """Update an existing pickup location.
        
        Updates the details of a pickup location identified by its code.
        
        Args:
            request: UpdatePickupLocationRequest containing:
                - code: Location code to update (required)
                - All other fields optional (only specified fields updated)
        
        Returns:
            UpdatePickupLocationResponse: Contains:
                - success: Whether update was successful
                - branch_id: ID of the updated location
                - pickup_location_code: The location code
        
        Raises:
            OTONotFoundError: If the location does not exist.
            OTOValidationError: If the update data is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.update_pickup_location(
            ...         UpdatePickupLocationRequest(
            ...             code="WH-001",
            ...             mobile="+966500000001"
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/updatePickupLocation",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return UpdatePickupLocationResponse.model_validate(data)
    
    async def get_pickup_locations(self) -> GetPickupLocationListResponse:
        """Get the list of all pickup locations.
        
        Retrieves all warehouses and branches configured for the account.
        
        Returns:
            GetPickupLocationListResponse: Contains:
                - success: Whether the request was successful
                - warehouses: List of warehouse locations
                - branches: List of branch locations
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     locations = await client.get_pickup_locations()
            ...     for wh in locations.warehouses:
            ...         print(f"Warehouse: {wh.name} ({wh.code})")
        """
        data = await self._request("GET", "/getPickupLocationList")
        return GetPickupLocationListResponse.model_validate(data)
    
    # =========================================================================
    # BRAND ENDPOINTS
    # =========================================================================
    
    async def get_brands(self) -> GetBrandListResponse:
        """Get the list of brands/client stores.
        
        Retrieves all brands configured for the account. Brands are used
        to group orders and manage multi-store operations.
        
        Returns:
            GetBrandListResponse: Contains:
                - success: Whether the request was successful
                - client_stores: List of Brand objects
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     brands = await client.get_brands()
            ...     for brand in brands.client_stores:
            ...         print(f"Brand: {brand.store_name}")
        """
        data = await self._request("GET", "/getBrandList")
        return GetBrandListResponse.model_validate(data)
    
    async def create_brand(self, request: CreateBrandRequest) -> CreateBrandResponse:
        """Create a new brand/client store.
        
        Creates a new brand for organizing orders and managing multi-store
        operations.
        
        Args:
            request: CreateBrandRequest containing:
                - store_name: Brand/store name (required)
                - logo: URL to brand logo (optional)
                - default_warehouse_id: Default warehouse ID (optional)
                - stores: List of store configurations (optional)
        
        Returns:
            CreateBrandResponse: Contains:
                - success: Whether creation was successful
                - client_store_id: ID of the created brand
        
        Raises:
            OTOConflictError: If the brand name already exists.
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     brand = await client.create_brand(
            ...         CreateBrandRequest(store_name="My Store")
            ...     )
            ...     print(f"Created brand ID: {brand.client_store_id}")
        """
        data = await self._request(
            "POST",
            "/createBrand",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreateBrandResponse.model_validate(data)
    
    # =========================================================================
    # PRODUCT ENDPOINTS
    # =========================================================================
    
    async def create_product(
        self,
        request: CreateProductRequest,
    ) -> CreateProductResponse:
        """Create a new product in the catalog.
        
        Creates a new product that can be included in orders and tracked
        for inventory management.
        
        Args:
            request: CreateProductRequest containing:
                - sku: Unique SKU identifier (required)
                - product_name: Display name (required)
                - price: Product price (required)
                - Optional: tax, description, barcode, images, etc.
        
        Returns:
            CreateProductResponse: Contains:
                - success: Whether creation was successful
                - product_id: ID of the created product
        
        Raises:
            OTOConflictError: If the SKU already exists.
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     product = await client.create_product(
            ...         CreateProductRequest(
            ...             sku="PRD-001",
            ...             product_name="Widget",
            ...             price="99.99"
            ...         )
            ...     )
            ...     print(f"Created product ID: {product.product_id}")
        """
        data = await self._request(
            "POST",
            "/createProduct",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return CreateProductResponse.model_validate(data)
    
    async def get_products(
        self,
        page_size: Optional[int] = None,
        current_page: Optional[int] = None,
    ) -> ProductListResponse:
        """Get the list of products in the catalog.
        
        Retrieves products with optional pagination.
        
        Args:
            page_size: Number of products per page (default 100).
            current_page: Page number (default 1).
        
        Returns:
            ProductListResponse: Contains:
                - success: Whether the request was successful
                - product_count: Total number of products
                - products: List of Product objects
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     products = await client.get_products(page_size=50)
            ...     for product in products.products:
            ...         print(f"{product.sku}: {product.name}")
        """
        data = await self._request(
            "GET",
            "/productList",
            params={"pageSize": page_size, "currentPage": current_page},
        )
        return ProductListResponse.model_validate(data)
    
    # =========================================================================
    # BOX ENDPOINTS
    # =========================================================================
    
    async def add_box(self, request: AddBoxRequest) -> AddBoxResponse:
        """Add a new box type for packaging.
        
        Creates a new box type that can be used for calculating
        volumetric weight.
        
        Args:
            request: AddBoxRequest containing:
                - name: Unique box name (required)
                - length: Length in cm (required)
                - width: Width in cm (required)
                - height: Height in cm (required)
        
        Returns:
            AddBoxResponse: Contains success flag and message.
        
        Raises:
            OTOConflictError: If the box name already exists.
            OTOValidationError: If required fields are missing.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.add_box(
            ...         AddBoxRequest(
            ...             name="Small Box",
            ...             length=20.0,
            ...             width=15.0,
            ...             height=10.0
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/addBox",
            json_data=request.model_dump(by_alias=True),
        )
        return AddBoxResponse.model_validate(data)
    
    async def update_box(self, request: UpdateBoxRequest) -> SuccessResponse:
        """Update an existing box type.
        
        Updates the dimensions of a box type identified by name.
        
        Args:
            request: UpdateBoxRequest containing:
                - name: Box name to update (required)
                - length: New length in cm (required)
                - width: New width in cm (required)
                - height: New height in cm (required)
        
        Returns:
            SuccessResponse: Contains success flag and optional message.
        
        Raises:
            OTONotFoundError: If the box does not exist.
            OTOValidationError: If the data is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.update_box(
            ...         UpdateBoxRequest(
            ...             name="Small Box",
            ...             length=22.0,
            ...             width=17.0,
            ...             height=12.0
            ...         )
            ...     )
        """
        data = await self._request(
            "POST",
            "/updateBox",
            json_data=request.model_dump(by_alias=True),
        )
        return SuccessResponse.model_validate(data)
    
    async def get_boxes(self) -> GetBoxResponse:
        """Get the list of box types.
        
        Retrieves all configured box types for the account.
        
        Returns:
            GetBoxResponse: Contains:
                - success: Whether the request was successful
                - boxes: List of Box objects
        
        Raises:
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     boxes = await client.get_boxes()
            ...     for box in boxes.boxes:
            ...         print(f"{box.box_name}: {box.length}x{box.width}x{box.height}")
        """
        data = await self._request("GET", "/getBox")
        return GetBoxResponse.model_validate(data)
    
    # =========================================================================
    # STOCK MANAGEMENT ENDPOINTS
    # =========================================================================
    
    async def update_stock_quantity(
        self,
        request: UpdateStockQuantityRequest,
    ) -> UpdateStockQuantityResponse:
        """Update the stock quantity for a product.
        
        Updates inventory levels for a product in a specific warehouse.
        
        Args:
            request: UpdateStockQuantityRequest containing:
                - sku: Product SKU to update (required)
                - quantity: New quantity or change amount (required)
                - action_type: How to apply (set/increment/decrement) (required)
                - warehouse_code: Target warehouse (optional)
        
        Returns:
            UpdateStockQuantityResponse: Contains:
                - success: Whether the update was successful
                - transaction_id: Stock transaction identifier
                - warnings: List of warning messages
        
        Raises:
            OTONotFoundError: If the SKU or warehouse does not exist.
            OTOValidationError: If the action type is invalid.
            OTOAuthenticationError: If authentication fails.
            OTONetworkError: If a network error occurs.
        
        Example:
            >>> async with OTOAsyncClient(refresh_token="your_token") as client:
            ...     result = await client.update_stock_quantity(
            ...         UpdateStockQuantityRequest(
            ...             sku="PRD-001",
            ...             quantity=100,
            ...             action_type="set"
            ...         )
            ...     )
            ...     print(f"Stock updated: {result.success}")
        """
        data = await self._request(
            "POST",
            "/updateStockQuantity",
            json_data=request.model_dump(by_alias=True, exclude_none=True),
        )
        return UpdateStockQuantityResponse.model_validate(data)


# Convenience function for creating clients
@asynccontextmanager
async def create_client(
    refresh_token: str,
    base_url: str = OTOAsyncClient.PRODUCTION_URL,
    timeout: float = 30.0,
) -> AsyncIterator[OTOAsyncClient]:
    """Create and manage an OTO API client as a context manager.
    
    This is a convenience function that creates an OTOAsyncClient and
    properly handles setup and teardown.
    
    Args:
        refresh_token: Permanent refresh token from OTO dashboard.
        base_url: API base URL (production or staging).
        timeout: Request timeout in seconds.
    
    Yields:
        OTOAsyncClient: An authenticated API client.
    
    Example:
        >>> async with create_client(refresh_token="your_token") as client:
        ...     orders = await client.get_orders()
        ...     print(f"Found {len(orders.orders)} orders")
    """
    async with OTOAsyncClient(
        refresh_token=refresh_token,
        base_url=base_url,
        timeout=timeout,
    ) as client:
        yield client
