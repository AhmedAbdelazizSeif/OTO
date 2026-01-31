# Models Reference

## Enums
- `PaymentMethod`: `cod`, `paid`
- `PickingType`: `PICKUP_BY_DC`, `BRANCH_DROP_OFF`
- `WhoPays`: `marketplacePaysDeliveryFee`, `sellerPaysDeliveryFee`
- `ServiceType`: `express`, `sameDay`, `fastDelivery`, `coldDelivery`, ...
- `DeliveryType`: `toCustomerDoorstep`, `pickupByCustomer`, ...
- `OrderStatus`: `assignedToWarehouse`, `searchingDriver`, `shipmentCreated`, `pickedUp`, `delivered`, `returned`, `canceled`, ...

## Order Models
- `OrderItem(product_id, name, price, quantity, sku, variant_id, image, weight, tax_amount)`
- `Customer(name, mobile, address, city, country, email, lat, lon, postcode, ...)`
- `CreateOrderRequest(order_id, payment_method, amount, amount_due, currency, customer, items, shipping_amount, ...)`
- `UpdateOrderRequest(order_id, shipping_notes, ...)`

## Shipment Models
- `CreateShipmentRequest(order_id, delivery_option_id, picking_type, who_pays, ...)`
- `CancelShipmentRequest(order_id, shipment_id)`
- `TrackShipmentRequest(tracking_number, delivery_company_name, status_history)`

## Delivery Models
- `CheckOTODeliveryFeeRequest(origin_city, destination_city, weight, ...)`
- `CheckDeliveryFeeRequest(origin_city, destination_city, weight, ...)`
- `DeliveryOption(delivery_option_id, delivery_option_name, price, currency, avg_delivery_time, ...)`

## Product Models
- `CreateProductRequest(sku, product_name, price, ...)`
- `UpdateStockQuantityRequest(sku, quantity, action_type, warehouse_code)`
