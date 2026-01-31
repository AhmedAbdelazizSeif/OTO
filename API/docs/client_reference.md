# OTOAsyncClient Reference

Class `OTOAsyncClient` in `API/client.py`

## Initialization
`__init__(refresh_token: str, base_url: str = PRODUCTION_URL, timeout: float = 30.0, auto_refresh: bool = True)`

## Auth Methods
- `access_token() -> str`: Get current access token.
- `token_expires_at() -> float`: Get token expiration timestamp.
- `is_token_expired() -> bool`: Check if token is expired.

## Order Methods
- `create_order(request: CreateOrderRequest) -> CreateOrderResponse`
- `update_order(request: UpdateOrderRequest) -> UpdateOrderResponse`
- `update_order_status(request: UpdateOrderStatusRequest) -> SuccessResponse`
- `cancel_order(order_id: str) -> SuccessResponse`
- `get_orders(status, from_date, to_date, per_page, page, payment_method, customer_phone, customer_name, destination_city, origin_city, order_id, delivery_company, brand_id, entity_id, parent_order_id, shipment_id) -> GetOrdersResponse`
- `hold_order(order_id, on_hold_reason, on_hold_reason_lang) -> SuccessResponse`
- `unhold_order(order_id) -> SuccessResponse`
- `get_order_details(order_id) -> OrderDetailsResponse`
- `check_order_availability(request: CheckOrderAvailabilityRequest) -> CheckOrderAvailabilityResponse`

## Shipment Methods
- `create_shipment(request: CreateShipmentRequest) -> CreateShipmentResponse`
- `cancel_shipment(order_id, shipment_id) -> SuccessResponse`
- `get_shipment_transactions(from_date, to_date, page, per_page) -> ShipmentTransactionsResponse`
- `get_shipping_price_transactions(order_id, shipment_id) -> GetShippingPriceTransactionsResponse`
- `track_shipment(request: TrackShipmentRequest) -> TrackShipmentResponse`
- `get_order_status(order_id) -> OrderTrackingResponse`
- `get_order_history(order_ids) -> OrderHistoryResponse`
- `print_awb(order_id) -> PrintAWBResponse`

## Return Methods
- `create_return_shipment(request: CreateReturnShipmentRequest) -> CreateReturnShipmentResponse`
- `get_return_link(order_id) -> GetReturnLinkResponse`
- `get_return_details(order_id) -> GetReturnDetailsResponse`
- `trigger_return_sms(order_id) -> TriggerReturnSmsResponse`

## Delivery & Fees
- `check_oto_delivery_fee(request: CheckOTODeliveryFeeRequest) -> CheckDeliveryFeeResponse`
- `check_delivery_fee(request: CheckDeliveryFeeRequest) -> CheckDeliveryFeeResponse`
- `get_delivery_fee(request: GetDeliveryFeeRequest) -> CheckDeliveryFeeResponse`
- `get_delivery_estimation(request: GetDeliveryEstimationRequest) -> SuccessResponse`
- `check_coverage(request: CheckCoverageRequest) -> SuccessResponse`

## Location & Config
- `get_cities(country, per_page, page) -> SuccessResponse`
- `create_pickup_location(request: CreatePickupLocationRequest) -> CreatePickupLocationResponse`
- `update_pickup_location(request: UpdatePickupLocationRequest) -> UpdatePickupLocationResponse`
- `get_pickup_locations() -> GetPickupLocationListResponse`
- `get_brands() -> GetBrandListResponse`
- `create_brand(request: CreateBrandRequest) -> CreateBrandResponse`
- `add_box(request: AddBoxRequest) -> AddBoxResponse`
- `update_box(request: UpdateBoxRequest) -> SuccessResponse`
- `get_boxes() -> GetBoxResponse`

## Products & Stock
- `create_product(request: CreateProductRequest) -> CreateProductResponse`
- `get_products(page_size, current_page) -> ProductListResponse`
- `update_stock_quantity(request: UpdateStockQuantityRequest) -> UpdateStockQuantityResponse`
