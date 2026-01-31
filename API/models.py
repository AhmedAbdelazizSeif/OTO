"""
Pydantic models for the OTO API V2.

This module contains all request and response models used by the OTO API client.
Models are organized by functional area (Orders, Shipments, etc.) and are
designed for easy introspection by MCP servers.

All models use Pydantic V2 syntax with strict type hints.
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, EmailStr


# =============================================================================
# ENUMS
# =============================================================================

class PaymentMethod(str, Enum):
    """Payment method for orders."""
    COD = "cod"
    PAID = "paid"


class PickingType(str, Enum):
    """How packages are collected from the sender."""
    PICKUP_BY_DC = "PICKUP_BY_DC"
    BRANCH_DROP_OFF = "BRANCH_DROP_OFF"


class WhoPays(str, Enum):
    """Who pays for the delivery fee."""
    MARKETPLACE_PAYS = "marketplacePaysDeliveryFee"
    SELLER_PAYS = "sellerPaysDeliveryFee"


class ServiceType(str, Enum):
    """Type of delivery service."""
    EXPRESS = "express"
    SAME_DAY = "sameDay"
    FAST_DELIVERY = "fastDelivery"
    COLD_DELIVERY = "coldDelivery"
    HEAVY_AND_BULKY = "heavyAndBulky"
    ELECTRONIC_AND_HEAVY = "electronicAndHeavy"
    PUDO = "pudo"
    LOCKER_DELIVERY = "lockerDelivery"


class DeliveryType(str, Enum):
    """Delivery destination type."""
    TO_CUSTOMER_DOORSTEP = "toCustomerDoorstep"
    PICKUP_BY_CUSTOMER = "pickupByCustomer"
    EITHER = "toCustomerDoorstepOrPickupByCustomer"


class OrderStatus(str, Enum):
    """Possible order statuses."""
    ASSIGNED_TO_WAREHOUSE = "assignedToWarehouse"
    SEARCHING_DRIVER = "searchingDriver"
    SHIPMENT_CREATED = "shipmentCreated"
    GOING_TO_PICKUP = "goingToPickup"
    PICKED_UP = "pickedUp"
    ARRIVED_TERMINAL = "arrivedTerminal"
    OUT_FOR_DELIVERY = "outForDelivery"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELED = "canceled"
    ON_HOLD = "onHold"


class PickupLocationType(str, Enum):
    """Type of pickup location."""
    BRANCH = "branch"
    WAREHOUSE = "warehouse"


class PickupLocationStatus(str, Enum):
    """Status of a pickup location."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class OnHoldReasonLang(str, Enum):
    """Supported languages for on-hold reasons."""
    ENGLISH = "en"
    TURKISH = "tr"
    ARABIC = "ar"


# =============================================================================
# BASE MODELS
# =============================================================================

class OTOBaseModel(BaseModel):
    """Base model with common configuration for all OTO models."""
    
    class Config:
        populate_by_name = True
        use_enum_values = True
        extra = "ignore"


# =============================================================================
# AUTHENTICATION MODELS
# =============================================================================

class RefreshTokenRequest(OTOBaseModel):
    """Request model for refreshing an access token.
    
    Args:
        refresh_token: The permanent refresh token obtained from the OTO UI.
            Used to obtain a new short-lived access token.
    """
    refresh_token: str = Field(
        ...,
        description="Permanent refresh token from OTO dashboard"
    )


class RefreshTokenResponse(OTOBaseModel):
    """Response model containing new authentication tokens.
    
    Args:
        access_token: Short-lived token (1 hour) for API authentication.
        refresh_token: Permanent token for obtaining new access tokens.
        success: Indicates if the token refresh was successful.
        token_type: Token type, typically 'Bearer'.
        expires_in: Token validity period in seconds.
    """
    access_token: str
    refresh_token: str
    success: bool
    token_type: str = "Bearer"
    expires_in: str


class HealthCheckResponse(OTOBaseModel):
    """Response model for API health check.
    
    Args:
        status: Health status, typically 'ok' when the API is operational.
    """
    status: str


# =============================================================================
# ACCOUNT MODELS
# =============================================================================

class AccountInfoResponse(OTOBaseModel):
    """Response model containing account information.
    
    Args:
        name: Full name of the account owner.
        email: Email address associated with the account.
        mobile: Mobile phone number for the account.
        package_name: Current subscription package name.
        remaining_credit: Available credit balance in the account.
        remaining_free_shipments: Number of free shipments from campaigns.
    """
    name: Optional[str] = None
    email: Optional[str] = None
    mobile: Optional[str] = None
    package_name: Optional[str] = Field(None, alias="packageName")
    remaining_credit: Optional[float] = Field(None, alias="remainingCredit")
    remaining_free_shipments: Optional[int] = Field(None, alias="remainingFreeShipments")


class BuyCreditRequest(OTOBaseModel):
    """Request model for purchasing account credit.
    
    Args:
        amount: The amount of credit to purchase in the account currency.
    """
    amount: float = Field(..., gt=0, description="Amount of credit to purchase")


class BuyCreditResponse(OTOBaseModel):
    """Response model after initiating a credit purchase.
    
    Args:
        success: Indicates if the request was successful.
        payment_url: URL to complete the payment process.
        payment_id: Unique identifier for the payment transaction.
    """
    success: bool
    payment_url: Optional[str] = Field(None, alias="paymentURL")
    payment_id: Optional[str] = Field(None, alias="paymentID")


class CreditTransaction(OTOBaseModel):
    """Model representing a single credit transaction.
    
    Args:
        id: Unique transaction identifier.
        amount: Transaction amount.
        order_id: Associated order ID.
        shipment_id: Associated shipment ID.
        description: Human-readable transaction description.
        transaction_date: Date and time of the transaction.
        transaction_type: Type of transaction (e.g., 'dcFee', 'otoFee').
        remaining_amount: Balance after this transaction.
        delivery_company_name: Name of the delivery company involved.
        charging_type: Type of charge (charge, refund, etc.).
        status: Transaction status (booked, revoked, canceled).
        oto_order_id: Internal OTO order identifier.
        order_payment_type: Payment method for the order.
        shipment_type: Type of shipment (forward, return, reverse).
    """
    id: int = Field(alias="ID")
    amount: float
    order_id: Optional[str] = Field(None, alias="orderID")
    shipment_id: Optional[str] = Field(None, alias="shipmentID")
    description: Optional[str] = None
    transaction_date: Optional[str] = Field(None, alias="transactionDate")
    transaction_type: Optional[str] = Field(None, alias="transactionType")
    remaining_amount: Optional[float] = Field(None, alias="remainingAmount")
    delivery_company_name: Optional[str] = Field(None, alias="deliveryCompanyName")
    charging_type: Optional[str] = Field(None, alias="chargingType")
    status: Optional[str] = None
    oto_order_id: Optional[int] = Field(None, alias="otoOrderID")
    order_payment_type: Optional[str] = Field(None, alias="orderPaymentType")
    shipment_type: Optional[str] = Field(None, alias="shipmentType")


class CreditTransactionsResponse(OTOBaseModel):
    """Response model for credit transactions list.
    
    Args:
        success: Indicates if the request was successful.
        transactions: List of credit transaction records.
    """
    success: bool
    transactions: List[CreditTransaction] = []


# =============================================================================
# MARKETPLACE MODELS
# =============================================================================

class RegisterRequest(OTOBaseModel):
    """Request model for registering a new vendor (marketplace use only).
    
    Args:
        company_name: Name of the vendor's company.
        email: Email address for the vendor account.
        full_name: Full name of the vendor contact.
        mobile_number: Mobile phone number for the vendor.
        cr_number: Commercial registration number (optional).
        vat_number: VAT registration number (optional).
        billing_address: Billing address for the vendor (optional).
        company_logo_url: URL to the company logo image (optional).
        webhook_url: URL for receiving webhook notifications (optional).
        webhook_method: HTTP method for webhooks, POST or GET (optional).
        webhook_secret_key: Secret key for webhook authentication (optional).
        currency: ISO 4217 currency code (e.g., SAR, USD) (optional).
    """
    company_name: str = Field(..., alias="companyName")
    email: EmailStr
    full_name: str = Field(..., alias="fullName")
    mobile_number: str = Field(..., alias="mobileNumber")
    cr_number: Optional[str] = Field(None, alias="crNumber")
    vat_number: Optional[str] = Field(None, alias="vatNumber")
    billing_address: Optional[str] = Field(None, alias="billingAddress")
    company_logo_url: Optional[str] = Field(None, alias="companyLogoURL")
    webhook_url: Optional[str] = Field(None, alias="webhookURL")
    webhook_method: Optional[str] = Field(None, alias="webhookMethod")
    webhook_secret_key: Optional[str] = Field(None, alias="webhookSecretKey")
    currency: Optional[str] = None


class RegisterResponse(OTOBaseModel):
    """Response model after vendor registration.
    
    Args:
        success: Indicates if registration was successful.
        activation_link: URL for the vendor to activate their account.
        refresh_token: Permanent token for the new vendor account.
    """
    success: bool
    activation_link: Optional[str] = Field(None, alias="activationLink")
    refresh_token: Optional[str] = Field(None, alias="refreshToken")


class ClientInfoRequest(OTOBaseModel):
    """Request model for retrieving client info by email.
    
    Args:
        email: Registered email address of the client.
    """
    email: EmailStr


class ClientInfoResponse(OTOBaseModel):
    """Response model containing client account information.
    
    Args:
        success: Indicates if the request was successful.
        remaining_credit: Available credit balance.
        validity_date: Account validity/expiration date.
        user_activated: Whether the user account is activated.
        refresh_token: Permanent token for the account.
        name: Client/company name.
        email: Registered email address.
        phone: Contact phone number.
    """
    success: bool
    remaining_credit: Optional[float] = Field(None, alias="remainingCredit")
    validity_date: Optional[str] = Field(None, alias="validityDate")
    user_activated: Optional[str] = Field(None, alias="userActivated")
    refresh_token: Optional[str] = Field(None, alias="refreshToken")
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


# =============================================================================
# CUSTOMER & ITEM MODELS
# =============================================================================

class Customer(OTOBaseModel):
    """Customer information for orders.
    
    Args:
        name: Customer's full name.
        mobile: Customer's mobile phone number.
        address: Full delivery address.
        city: Destination city name.
        country: ISO2 country code (e.g., SA, AE, EG).
        email: Customer's email address (optional).
        district: District or area name (optional).
        state: State or province name (optional).
        postcode: Postal/ZIP code (optional).
        street: Street name (optional).
        building_no: Building number from national address (optional).
        secondary_address_number: Additional number in national address (optional).
        short_address_code: Simplified address code (optional).
        lat: Latitude coordinate (optional).
        lon: Longitude coordinate (optional).
        ref_id: External customer reference ID (optional).
        w3w_address: What3Words address (optional).
    """
    name: str
    mobile: str
    address: str
    city: str
    country: str
    email: Optional[EmailStr] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postcode: Optional[str] = None
    street: Optional[str] = None
    building_no: Optional[str] = Field(None, alias="buildingNo")
    secondary_address_number: Optional[str] = Field(None, alias="secondaryAddressNumber")
    short_address_code: Optional[str] = Field(None, alias="shortAddressCode")
    lat: Optional[float] = None
    lon: Optional[float] = None
    ref_id: Optional[str] = Field(None, alias="refID")
    w3w_address: Optional[str] = Field(None, alias="W3WAddress")


class OrderItem(OTOBaseModel):
    """Individual item within an order.
    
    Args:
        name: Product name (optional in responses).
        sku: Stock Keeping Unit identifier (optional in responses).
        price: Unit price of the product (optional in responses).
        quantity: Number of units ordered.
        product_id: Internal product identifier (optional).
        row_total: Total amount for this line item (optional).
        tax_amount: Tax amount for this line item (optional).
        serial_number: Product serial number (optional).
        image: URL to product image (optional).
        hs_code: Harmonized System code for customs (optional).
        item_origin: Country of origin (optional).
    """
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    quantity: int = Field(..., ge=1)
    product_id: Optional[int] = Field(None, alias="productId")
    row_total: Optional[float] = Field(None, alias="rowTotal")
    tax_amount: Optional[float] = Field(None, alias="taxAmount")
    serial_number: Optional[str] = Field(None, alias="serialnumber")
    image: Optional[str] = None
    hs_code: Optional[str] = Field(None, alias="hsCode")
    item_origin: Optional[str] = Field(None, alias="itemOrigin")


class SenderInformation(OTOBaseModel):
    """Sender information for orders.
    
    Args:
        sender_id: Unique identifier for the sender.
        sender_full_name: Full name of the sender.
        sender_mobile: Mobile phone number.
        sender_country: ISO2 country code.
        sender_city: City name.
        sender_address_line: Full address line.
        sender_address_name: Name for this address (optional).
        sender_email: Email address (optional).
        sender_short_address_code: Short address code (optional).
        sender_building_no: Building number (optional).
        sender_secondary_address_number: Secondary address number (optional).
        sender_state: State or province (optional).
        sender_district: District name (optional).
        sender_street: Street name (optional).
        sender_postcode: Postal code (optional).
        lat: Latitude coordinate (optional).
        lon: Longitude coordinate (optional).
    """
    sender_id: str = Field(..., alias="senderId")
    sender_full_name: str = Field(..., alias="senderFullName")
    sender_mobile: str = Field(..., alias="senderMobile")
    sender_country: str = Field(..., alias="senderCountry")
    sender_city: str = Field(..., alias="senderCity")
    sender_address_line: str = Field(..., alias="senderAddressLine")
    sender_address_name: Optional[str] = Field(None, alias="senderAddressName")
    sender_email: Optional[str] = Field(None, alias="senderEmail")
    sender_short_address_code: Optional[str] = Field(None, alias="senderShortAddressCode")
    sender_building_no: Optional[str] = Field(None, alias="senderBuildingNo")
    sender_secondary_address_number: Optional[str] = Field(None, alias="sendersecondaryAddressNumber")
    sender_state: Optional[str] = Field(None, alias="senderState")
    sender_district: Optional[str] = Field(None, alias="senderDistrict")
    sender_street: Optional[str] = Field(None, alias="senderStreet")
    sender_postcode: Optional[str] = Field(None, alias="senderPostcode")
    lat: Optional[float] = None
    lon: Optional[float] = None


# =============================================================================
# ORDER MODELS
# =============================================================================

class CreateOrderRequest(OTOBaseModel):
    """Request model for creating a new order in OTO.
    
    Args:
        order_id: Unique identifier for the order in your system.
        payment_method: Payment method (cod or paid).
        amount: Total value of the order.
        amount_due: Amount due from customer (0 if paid, equals amount if COD).
        currency: ISO 4217 currency code (e.g., SAR).
        customer: Customer details including delivery address.
        items: List of items in the order.
        parent_order_id: Parent order ID for split orders (optional).
        entity_id: Sales channel entity identifier (optional).
        ref1: Custom reference field (optional).
        pickup_location_code: Code for pickup warehouse/branch (optional).
        create_shipment: Whether to automatically create a shipment (optional).
        service_type: 'pickupFromStore' for store pickup orders (optional).
        for_reverse_shipment: Allow reverse shipment without forward (optional).
        delivery_option_id: Specific delivery company option ID (optional).
        store_name: Name of the store (optional).
        picking_type: PICKUP_BY_DC or BRANCH_DROP_OFF (optional).
        shipping_amount: Shipping cost (optional).
        subtotal: Order subtotal before shipping (optional).
        shipping_notes: Special instructions for delivery (optional).
        package_size: Maximum package size identifier (optional).
        package_count: Number of packages (optional).
        package_weight: Total weight in kg (optional).
        box_width: Package width in cm (optional).
        box_length: Package length in cm (optional).
        box_height: Package height in cm (optional).
        delivery_slot_date: Preferred delivery date (optional).
        delivery_slot_from: Delivery window start time (optional).
        delivery_slot_to: Delivery window end time (optional).
        order_date: Original order creation date (optional).
        sender_name: Sender's name (optional).
        sender_information: Detailed sender information (optional).
        coupon_code: Discount coupon code (optional).
        cod_fee: Cash on delivery fee (optional).
        brand_id: Brand/client store identifier (optional).
        who_pays: Who pays for shipping (optional).
        front_side_id_card: URL to front of ID card for intl shipments (optional).
        back_side_id_card: URL to back of ID card for intl shipments (optional).
    """
    order_id: str = Field(..., alias="orderId")
    payment_method: PaymentMethod
    amount: float
    amount_due: float = Field(..., alias="amount_due")
    currency: str
    customer: Customer
    items: List[OrderItem]
    parent_order_id: Optional[str] = Field(None, alias="parentOrderId")
    entity_id: Optional[int] = Field(None, alias="entityId")
    ref1: Optional[str] = None
    pickup_location_code: Optional[str] = Field(None, alias="pickupLocationCode")
    create_shipment: Optional[bool] = Field(None, alias="createShipment")
    service_type: Optional[str] = Field(None, alias="serviceType")
    for_reverse_shipment: Optional[bool] = Field(None, alias="forReverseShipment")
    delivery_option_id: Optional[int] = Field(None, alias="deliveryOptionId")
    store_name: Optional[str] = Field(None, alias="storeName")
    picking_type: Optional[PickingType] = Field(None, alias="pickingType")
    shipping_amount: Optional[float] = Field(None, alias="shippingAmount")
    subtotal: Optional[float] = None
    shipping_notes: Optional[str] = Field(None, alias="shippingNotes")
    package_size: Optional[str] = Field(None, alias="packageSize")
    package_count: Optional[int] = Field(None, alias="packageCount")
    package_weight: Optional[float] = Field(None, alias="packageWeight")
    box_width: Optional[float] = Field(None, alias="boxWidth")
    box_length: Optional[float] = Field(None, alias="boxLength")
    box_height: Optional[float] = Field(None, alias="boxHeight")
    delivery_slot_date: Optional[str] = Field(None, alias="deliverySlotDate")
    delivery_slot_from: Optional[str] = Field(None, alias="deliverySlotFrom")
    delivery_slot_to: Optional[str] = Field(None, alias="deliverySlotTo")
    order_date: Optional[str] = Field(None, alias="orderDate")
    sender_name: Optional[str] = Field(None, alias="senderName")
    sender_information: Optional[SenderInformation] = Field(None, alias="senderInformation")
    coupon_code: Optional[str] = Field(None, alias="couponCode")
    cod_fee: Optional[float] = Field(None, alias="codFee")
    brand_id: Optional[int] = Field(None, alias="brandId")
    who_pays: Optional[WhoPays] = Field(None, alias="whoPays")
    front_side_id_card: Optional[str] = Field(None, alias="frontSideIDCard")
    back_side_id_card: Optional[str] = Field(None, alias="backSideIDCard")


class CreateOrderResponse(OTOBaseModel):
    """Response model after creating an order.
    
    Args:
        success: Indicates if the order was created successfully.
        oto_id: Internal OTO identifier for the created order.
    """
    success: bool
    oto_id: Optional[int] = Field(None, alias="otoId")


class UpdateOrderRequest(OTOBaseModel):
    """Request model for updating an existing order.
    
    Note: Orders can only be updated before shipment creation.
    If a shipment exists, cancel it first.
    
    Args:
        order_id: The order ID to update.
        customer: Updated customer information (optional).
        items: Updated list of items (optional).
        ref1: Updated reference field (optional).
        pickup_location_code: Updated pickup location (optional).
        delivery_option_id: Updated delivery option (optional).
        store_name: Updated store name (optional).
        payment_method: Updated payment method (optional).
        amount: Updated order total (optional).
        amount_due: Updated amount due (optional).
        shipping_amount: Updated shipping cost (optional).
        subtotal: Updated subtotal (optional).
        currency: Updated currency (optional).
        customs_value: Updated customs value (optional).
        customs_currency: Updated customs currency (optional).
        shipping_notes: Updated shipping notes (optional).
        package_size: Updated package size (optional).
        package_count: Updated package count (optional).
        package_weight: Updated weight (optional).
        box_width: Updated width (optional).
        box_length: Updated length (optional).
        box_height: Updated height (optional).
        order_date: Updated order date (optional).
        delivery_slot_date: Updated delivery date (optional).
        delivery_slot_from: Updated delivery window start (optional).
        delivery_slot_to: Updated delivery window end (optional).
    """
    order_id: str = Field(..., alias="orderId")
    customer: Optional[Customer] = None
    items: Optional[List[OrderItem]] = None
    ref1: Optional[str] = None
    pickup_location_code: Optional[str] = Field(None, alias="pickupLocationCode")
    delivery_option_id: Optional[str] = Field(None, alias="deliveryOptionId")
    store_name: Optional[str] = Field(None, alias="storeName")
    payment_method: Optional[PaymentMethod] = None
    amount: Optional[float] = None
    amount_due: Optional[float] = None
    shipping_amount: Optional[float] = Field(None, alias="shippingAmount")
    subtotal: Optional[float] = None
    currency: Optional[str] = None
    customs_value: Optional[str] = Field(None, alias="customsValue")
    customs_currency: Optional[str] = Field(None, alias="customsCurrency")
    shipping_notes: Optional[str] = Field(None, alias="shippingNotes")
    package_size: Optional[str] = Field(None, alias="packageSize")
    package_count: Optional[int] = Field(None, alias="packageCount")
    package_weight: Optional[float] = Field(None, alias="packageWeight")
    box_width: Optional[float] = Field(None, alias="boxWidth")
    box_length: Optional[float] = Field(None, alias="boxLength")
    box_height: Optional[float] = Field(None, alias="boxHeight")
    order_date: Optional[str] = Field(None, alias="orderDate")
    delivery_slot_date: Optional[str] = Field(None, alias="deliverySlotDate")
    delivery_slot_from: Optional[str] = Field(None, alias="deliverySlotFrom")
    delivery_slot_to: Optional[str] = Field(None, alias="deliverySlotTo")


class UpdateOrderResponse(OTOBaseModel):
    """Response model after updating an order.
    
    Args:
        success: Indicates if the update was successful.
        message: Success or error message.
    """
    success: bool
    message: Optional[str] = None


class UpdateOrderStatusRequest(OTOBaseModel):
    """Request model for updating order status.
    
    Args:
        order_ids: List of order IDs to update.
        status: New status (delivered, returned, pickedUp).
        description: Optional description of the status change.
        date: Optional delivery/update date.
    """
    order_ids: List[str] = Field(..., alias="orderIds")
    status: str
    description: Optional[str] = None
    date: Optional[str] = None


class CancelOrderRequest(OTOBaseModel):
    """Request model for canceling an order.
    
    Note: Orders with shipments cannot be canceled via this endpoint.
    
    Args:
        order_id: The order ID to cancel.
    """
    order_id: str = Field(..., alias="orderId")


class HoldOrderRequest(OTOBaseModel):
    """Request model for placing an order on hold.
    
    Args:
        order_id: The order ID to place on hold.
        on_hold_reason: Reason for placing the order on hold.
        on_hold_reason_lang: Language code for the reason (en, tr, ar).
    """
    order_id: str = Field(..., alias="orderId")
    on_hold_reason: str = Field(..., alias="onHoldReason")
    on_hold_reason_lang: OnHoldReasonLang = Field(..., alias="onHoldReasonLang")


class UnholdOrderRequest(OTOBaseModel):
    """Request model for releasing an order from hold.
    
    Args:
        order_id: The order ID to release from hold.
    """
    order_id: str = Field(..., alias="orderId")


class StatusHistoryEntry(OTOBaseModel):
    """Single entry in an order's status history.
    
    Args:
        date: Timestamp of the status change.
        status: The status at this point.
        description: Optional description of the change.
        delivery_company: Delivery company involved (optional).
        shipment_id: Associated shipment ID (optional).
    """
    date: str
    status: str
    description: Optional[str] = None
    delivery_company: Optional[str] = Field(None, alias="deliveryCompany")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")


class OrderDetailsResponse(OTOBaseModel):
    """Response model for order details.
    
    Args:
        success: Indicates if the request was successful.
        order_id: The order identifier.
        status: Current order status.
        id: Internal OTO order ID.
        amount: Order total amount.
        amount_due: Amount due from customer.
        currency: Order currency.
        payment_method: Payment method used.
        items: List of items in the order.
        status_history: History of status changes.
        tracking_url: URL for tracking the shipment.
        dc_name: Delivery company name.
        pickup_location: Pickup location name.
        delivery_option_id: Delivery option identifier.
        package_count: Number of packages.
        package_weight: Total weight.
        customs_value: Customs declared value.
        customs_currency: Customs value currency.
        order_date: Original order date.
        delivery_slot_date: Scheduled delivery date.
        delivery_slot_from: Delivery window start.
        delivery_slot_to: Delivery window end.
    """
    success: bool
    order_id: Optional[str] = Field(None, alias="orderId")
    status: Optional[str] = None
    id: Optional[int] = None
    amount: Optional[float] = None
    amount_due: Optional[float] = None
    currency: Optional[str] = None
    payment_method: Optional[str] = None
    items: Optional[List[OrderItem]] = None
    status_history: Optional[List[StatusHistoryEntry]] = Field(None, alias="statusHistory")
    tracking_url: Optional[str] = Field(None, alias="trackingURL")
    dc_name: Optional[str] = Field(None, alias="dcName")
    pickup_location: Optional[str] = Field(None, alias="pickupLocation")
    delivery_option_id: Optional[int] = Field(None, alias="deliveryOptionId")
    package_count: Optional[int] = Field(None, alias="packageCount")
    package_weight: Optional[float] = Field(None, alias="packageWeight")
    customs_value: Optional[float] = Field(None, alias="customsValue")
    customs_currency: Optional[str] = Field(None, alias="customsCurrency")
    order_date: Optional[str] = Field(None, alias="orderDate")
    delivery_slot_date: Optional[str] = Field(None, alias="deliverySlotDate")
    delivery_slot_from: Optional[str] = Field(None, alias="deliverySlotFrom")
    delivery_slot_to: Optional[str] = Field(None, alias="deliverySlotTo")


class Order(OTOBaseModel):
    """Order summary model for listing orders.
    
    Args:
        id: Internal OTO order ID.
        order_id: External order identifier.
        status: Current order status.
        customer: Customer information.
        items: List of items.
        amount: Order total.
        total_due: Amount due from customer.
        currency: Order currency.
        payment_method: Payment method.
        order_date: Order creation date.
        delivery_date: Actual/scheduled delivery date.
        customer_name: Customer's name.
        customer_phone: Customer's phone.
        customer_address: Delivery address.
        origin_city: Pickup city.
        destination_city: Delivery city.
        destination_country: Delivery country code.
        tracking_url: Tracking URL.
        shipment_number: Associated shipment number.
        package_count: Number of packages.
        weight: Total weight.
    """
    id: str
    order_id: str = Field(alias="orderId")
    status: str
    customer: Optional[Customer] = None
    items: Optional[List[OrderItem]] = None
    amount: Optional[float] = None
    total_due: Optional[float] = Field(None, alias="totalDue")
    currency: Optional[str] = None
    payment_method: Optional[str] = Field(None, alias="paymentMethod")
    order_date: Optional[str] = Field(None, alias="orderDate")
    delivery_date: Optional[str] = Field(None, alias="deliveryDate")
    customer_name: Optional[str] = Field(None, alias="customerName")
    customer_phone: Optional[str] = Field(None, alias="customerPhone")
    customer_address: Optional[str] = Field(None, alias="customerAddress")
    origin_city: Optional[str] = Field(None, alias="originCity")
    destination_city: Optional[str] = Field(None, alias="destinationCity")
    destination_country: Optional[str] = Field(None, alias="destinationCountry")
    tracking_url: Optional[str] = Field(None, alias="trackingURL")
    shipment_number: Optional[str] = Field(None, alias="shipmentNumber")
    package_count: Optional[int] = Field(None, alias="packageCount")
    weight: Optional[float] = None


class GetOrdersResponse(OTOBaseModel):
    """Response model for listing orders.
    
    Args:
        success: Indicates if the request was successful.
        orders: List of order summaries.
        per_page: Number of orders per page.
        current_page: Current page number.
        total_page: Total number of pages.
        total_count: Total number of orders.
    """
    success: bool
    orders: List[Order] = []
    per_page: Optional[int] = Field(None, alias="perPage")
    current_page: Optional[int] = Field(None, alias="currentPage")
    total_page: Optional[int] = Field(None, alias="totalPage")
    total_count: Optional[int] = Field(None, alias="totalCount")


class CheckOrderAvailabilityRequest(OTOBaseModel):
    """Request model for checking order availability.
    
    Args:
        order_id: Order ID to check availability for.
        rule_ids: Optional list of OMS rule IDs to use.
    """
    order_id: str = Field(..., alias="orderId")
    rule_ids: Optional[List[str]] = Field(None, alias="ruleIds")


class LocationCoordinates(OTOBaseModel):
    """Geographic coordinates for a location.
    
    Args:
        lat: Latitude.
        lon: Longitude.
    """
    lat: float
    lon: float


class AvailableLocation(OTOBaseModel):
    """Location where an order can be fulfilled.
    
    Args:
        location_name: Name of the fulfillment location.
        location_code: Code identifier for the location.
        distance: Distance from destination.
        location_coordinates: Geographic coordinates.
    """
    location_name: str = Field(alias="locationName")
    location_code: str = Field(alias="locationCode")
    distance: float
    location_coordinates: LocationCoordinates = Field(alias="locationCoordinates")


class CheckOrderAvailabilityResponse(OTOBaseModel):
    """Response model for order availability check.
    
    Args:
        success: Indicates if the check was successful.
        order_availability: Availability status string.
        locations: List of locations where order can be fulfilled.
    """
    success: bool
    order_availability: Optional[str] = Field(None, alias="orderAvailability")
    locations: List[AvailableLocation] = []


# =============================================================================
# SHIPMENT MODELS
# =============================================================================

class CreateShipmentRequest(OTOBaseModel):
    """Request model for creating a shipment for an order.
    
    Args:
        order_id: The order ID to create a shipment for.
        delivery_option_id: Specific delivery company option ID (optional).
        picking_type: PICKUP_BY_DC or BRANCH_DROP_OFF (optional).
        who_pays: Who pays for the shipment (optional).
        front_side_id_card: URL to front of ID for intl shipments (optional).
        back_side_id_card: URL to back of ID for intl shipments (optional).
    """
    order_id: str = Field(..., alias="orderId")
    delivery_option_id: Optional[str] = Field(None, alias="deliveryOptionId")
    picking_type: Optional[PickingType] = Field(None, alias="pickingType")
    who_pays: Optional[WhoPays] = Field(None, alias="whoPays")
    front_side_id_card: Optional[str] = Field(None, alias="frontSideIDCard")
    back_side_id_card: Optional[str] = Field(None, alias="backSideIDCard")


class CreateShipmentResponse(OTOBaseModel):
    """Response model after creating a shipment.
    
    Args:
        success: Indicates if the shipment was created successfully.
        message: Status message.
    """
    success: bool
    message: Optional[str] = None


class CancelShipmentRequest(OTOBaseModel):
    """Request model for canceling a shipment.
    
    Note: Shipments cannot be canceled after pickup.
    
    Args:
        order_id: The order ID associated with the shipment.
        shipment_id: The shipment ID to cancel.
    """
    order_id: str = Field(..., alias="orderId")
    shipment_id: str = Field(..., alias="shipmentId")


class ShipmentTransaction(OTOBaseModel):
    """Model representing a shipment transaction record.
    
    Args:
        shipment_number: Unique shipment identifier.
        order_id: Associated order ID.
        shipment_creation_date: When the shipment was created.
        delivery_company_name: Name of the delivery company.
        dc_connection_name: Connection/account name with the DC.
        shipment_type: Type of shipment (Forward, Return).
        dc_charge: Delivery company charge.
        currency: Charge currency.
        original_weight: Originally declared weight.
        dc_updated_weight: Weight updated by delivery company.
        status: Shipment status.
        dc_invoice_number: Delivery company invoice number.
    """
    shipment_number: Optional[str] = Field(None, alias="shipmentNumber")
    order_id: Optional[str] = Field(None, alias="orderId")
    shipment_creation_date: Optional[str] = Field(None, alias="shipmentCreationDate")
    delivery_company_name: Optional[str] = Field(None, alias="deliveryCompanyName")
    dc_connection_name: Optional[str] = Field(None, alias="dcConnectionName")
    shipment_type: Optional[str] = Field(None, alias="shipmentType")
    dc_charge: Optional[float] = Field(None, alias="dcCharge")
    currency: Optional[str] = None
    original_weight: Optional[float] = Field(None, alias="originalWeight")
    dc_updated_weight: Optional[float] = Field(None, alias="dcUpdatedWeight")
    status: Optional[str] = None
    dc_invoice_number: Optional[str] = Field(None, alias="dcInvoiceNumber")


class ShipmentTransactionsResponse(OTOBaseModel):
    """Response model for shipment transactions list.
    
    Args:
        success: Indicates if the request was successful.
        shipments: List of shipment transaction records.
    """
    success: bool
    shipments: List[ShipmentTransaction] = []


class GetShippingPriceTransactionsRequest(OTOBaseModel):
    """Request model for shipping price transactions.
    
    Args:
        order_id: Order ID to get transactions for.
        shipment_id: Shipment ID to get transactions for.
    """
    order_id: Optional[str] = Field(None, alias="orderId")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")


class ShippingPriceTransaction(OTOBaseModel):
    """Model representing a shipping price transaction.
    
    Args:
        id: Transaction identifier.
        amount: Transaction amount.
        order_id: Associated order ID.
        shipment_id: Associated shipment ID.
        description: Transaction description.
        order_status: Order status at transaction time.
        transaction_date: When the transaction occurred.
        oto_order_id: Internal OTO order ID.
        delivery_name: Delivery company name.
        transaction: Transaction type.
        status: Transaction status.
    """
    id: int = Field(alias="ID")
    amount: float
    order_id: Optional[str] = Field(None, alias="orderID")
    shipment_id: Optional[str] = Field(None, alias="shipmentID")
    description: Optional[str] = None
    order_status: Optional[str] = Field(None, alias="orderStatus")
    transaction_date: Optional[str] = Field(None, alias="transactionDate")
    oto_order_id: Optional[int] = Field(None, alias="otoOrderID")
    delivery_name: Optional[str] = Field(None, alias="deliveryName")
    transaction: Optional[str] = None
    status: Optional[str] = None


class GetShippingPriceTransactionsResponse(OTOBaseModel):
    """Response model for shipping price transactions.
    
    Args:
        success: Indicates if the request was successful.
        count: Number of transactions returned.
        shipping_transactions: List of shipping price transactions.
    """
    success: bool
    count: Optional[int] = None
    shipping_transactions: List[ShippingPriceTransaction] = Field(
        default=[], alias="shippingTransactions"
    )


# =============================================================================
# RETURN SHIPMENT MODELS
# =============================================================================

class ReturnItem(OTOBaseModel):
    """Item being returned.
    
    Args:
        sku: SKU of the item to return.
        quantity: Quantity being returned.
    """
    sku: str
    quantity: int = Field(..., ge=1)


class CreateReturnShipmentRequest(OTOBaseModel):
    """Request model for creating a return/reverse shipment.
    
    Args:
        order_id: The delivered order ID to create a return for.
        delivery_option_id: Specific delivery option ID (optional).
        pickup_location_code: Return destination location code (optional).
        picking_type: PICKUP_BY_DC or BRANCH_DROP_OFF (optional).
        front_side_id_card: URL to front of ID for intl shipments (optional).
        back_side_id_card: URL to back of ID for intl shipments (optional).
        items: List of items being returned (optional).
    """
    order_id: str = Field(..., alias="orderId")
    delivery_option_id: Optional[str] = Field(None, alias="deliveryOptionId")
    pickup_location_code: Optional[str] = Field(None, alias="pickupLocationCode")
    picking_type: Optional[PickingType] = Field(None, alias="pickingType")
    front_side_id_card: Optional[str] = Field(None, alias="frontSideIDCard")
    back_side_id_card: Optional[str] = Field(None, alias="backSideIDCard")
    items: Optional[List[ReturnItem]] = None


class CreateReturnShipmentResponse(OTOBaseModel):
    """Response model after creating a return shipment.
    
    Args:
        success: Indicates if the return shipment was created.
        msg: Status message.
    """
    success: bool
    msg: Optional[str] = None


class GetReturnLinkRequest(OTOBaseModel):
    """Request model for getting a customer return link.
    
    Args:
        order_id: The order ID to generate a return link for.
    """
    order_id: str = Field(..., alias="orderId")


class GetReturnLinkResponse(OTOBaseModel):
    """Response model containing the return portal link.
    
    Args:
        success: Indicates if the link was generated successfully.
        return_link: URL for the customer return portal.
    """
    success: bool
    return_link: Optional[str] = Field(None, alias="returnLink")


class GetReturnDetailsRequest(OTOBaseModel):
    """Request model for getting return shipment details.
    
    Args:
        order_id: The order ID to get return details for.
    """
    order_id: str = Field(..., alias="orderId")


class ReturnItemDetail(OTOBaseModel):
    """Detail about an item in a return.
    
    Args:
        sku: Item SKU.
        quantity_ordered: Original quantity ordered.
        quantity_to_be_returned: Quantity being returned (optional).
    """
    sku: str
    quantity_ordered: int = Field(alias="quantityOrdered")
    quantity_to_be_returned: Optional[int] = Field(None, alias="quantityToBeReturned")


class GetReturnDetailsResponse(OTOBaseModel):
    """Response model for return shipment details.
    
    Args:
        order_id: The order ID.
        status: Current return status.
        return_reason: Reason for the return.
        return_location_code: Destination location for returns.
        items: List of items in the return.
    """
    order_id: Optional[str] = Field(None, alias="orderId")
    status: Optional[str] = None
    return_reason: Optional[str] = Field(None, alias="returnReason")
    return_location_code: Optional[str] = Field(None, alias="returnLocationCode")
    items: List[ReturnItemDetail] = []


class TriggerReturnSmsRequest(OTOBaseModel):
    """Request model for triggering a return SMS notification.
    
    Args:
        order_id: The order ID to send return SMS for.
    """
    order_id: str = Field(..., alias="orderId")


class TriggerReturnSmsResponse(OTOBaseModel):
    """Response model after triggering return SMS.
    
    Args:
        success: Indicates if the SMS was triggered.
        oto_id: Internal OTO identifier.
    """
    success: bool
    oto_id: Optional[int] = Field(None, alias="otoId")


# =============================================================================
# TRACKING MODELS
# =============================================================================

class OrderTrackingRequest(OTOBaseModel):
    """Request model for tracking an order.
    
    Args:
        order_id: The order ID to track.
    """
    order_id: str = Field(..., alias="orderId")


class OrderTrackingResponse(OTOBaseModel):
    """Response model for order tracking status.
    
    Args:
        order_id: The tracked order ID.
        status: Current order status.
        delivery_company: Delivery company handling the shipment.
        shipment_id: Shipment identifier.
        dc_tracking_number: Delivery company tracking number.
        date: Last update date/time.
        note: Optional status note.
        delivery_slot_date: Scheduled delivery date.
        print_awb_url: URL to print the shipping label.
    """
    order_id: Optional[str] = Field(None, alias="orderId")
    status: Optional[str] = None
    delivery_company: Optional[str] = Field(None, alias="deliveryCompany")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")
    dc_tracking_number: Optional[str] = Field(None, alias="dcTrackingNumber")
    date: Optional[str] = None
    note: Optional[str] = None
    delivery_slot_date: Optional[str] = Field(None, alias="deliverySlotDate")
    print_awb_url: Optional[str] = Field(None, alias="printAWBURL")


class OrderHistoryRequest(OTOBaseModel):
    """Request model for getting order history.
    
    Args:
        order_ids: List of order IDs to get history for.
    """
    order_ids: List[str] = Field(..., alias="orderIds")


class HistoryEvent(OTOBaseModel):
    """Single event in order/shipment history.
    
    Args:
        date: When the event occurred.
        status: Status at this event.
        description: Event description.
        delivery_company: Delivery company involved (optional).
        shipment_id: Associated shipment ID (optional).
    """
    date: str
    status: str
    description: Optional[str] = None
    delivery_company: Optional[str] = Field(None, alias="deliveryCompany")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")


class OrderHistoryItem(OTOBaseModel):
    """History for a single order.
    
    Args:
        order_id: The order identifier.
        branch_name: Branch handling the order.
        warehouse_name: Warehouse name (optional).
        delivery_company: Delivery company.
        shipment_id: Shipment identifier.
        dc_tracking_number: Delivery company tracking number.
        status: Current status.
        driver_name: Assigned driver's name.
        driver_phone: Driver's phone number.
        tracking_url: Tracking URL.
        history: List of historical events.
    """
    order_id: str = Field(alias="orderId")
    branch_name: Optional[str] = Field(None, alias="branchName")
    warehouse_name: Optional[str] = Field(None, alias="warehouseName")
    delivery_company: Optional[str] = Field(None, alias="deliveryCompany")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")
    dc_tracking_number: Optional[str] = Field(None, alias="dcTrackingNumber")
    status: Optional[str] = None
    driver_name: Optional[str] = Field(None, alias="driverName")
    driver_phone: Optional[str] = Field(None, alias="driverPhone")
    tracking_url: Optional[str] = Field(None, alias="trackingUrl")
    history: List[HistoryEvent] = []


class OrderHistoryResponse(OTOBaseModel):
    """Response model for order history.
    
    Args:
        success: Indicates if the request was successful.
        items: List of order history items.
    """
    success: bool
    items: List[OrderHistoryItem] = []


class TrackShipmentRequest(OTOBaseModel):
    """Request model for tracking a shipment by tracking number.
    
    Args:
        tracking_number: The shipment/tracking number.
        delivery_company_name: Name/code of the delivery company.
        status_history: Whether to include full history.
        brand_name: Associated brand name (optional).
    """
    tracking_number: str = Field(..., alias="trackingNumber")
    delivery_company_name: str = Field(..., alias="deliveryCompanyName")
    status_history: bool = Field(..., alias="statusHistory")
    brand_name: Optional[str] = Field(None, alias="brandName")


class ShipmentTrackingEvent(OTOBaseModel):
    """Single tracking event from delivery company.
    
    Args:
        dc_status: Delivery company status code.
        oto_status: OTO-normalized status.
        dc_update_date: When DC reported this status.
        dc_description: DC's description of the event.
        shipment_id: Shipment identifier.
        update_status_date: Whether this updated the status date.
    """
    dc_status: Optional[str] = Field(None, alias="dcStatus")
    oto_status: Optional[str] = Field(None, alias="otoStatus")
    dc_update_date: Optional[str] = Field(None, alias="dcUpdateDate")
    dc_description: Optional[str] = Field(None, alias="dcDescription")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")
    update_status_date: Optional[bool] = Field(None, alias="updateStatusDate")


class ShipmentTrackingItem(OTOBaseModel):
    """Tracking information for a shipment.
    
    Args:
        dc_status: Current DC status code.
        oto_status: Current OTO-normalized status.
        dc_update_date: Last DC update date.
        dc_description: Current status description.
        shipment_id: Shipment identifier.
        success: Whether tracking was successful.
        history: List of historical tracking events.
    """
    dc_status: Optional[str] = Field(None, alias="dcStatus")
    oto_status: Optional[str] = Field(None, alias="otoStatus")
    dc_update_date: Optional[str] = Field(None, alias="dcUpdateDate")
    dc_description: Optional[str] = Field(None, alias="dcDescription")
    shipment_id: Optional[str] = Field(None, alias="shipmentId")
    success: Optional[bool] = None
    history: List[ShipmentTrackingEvent] = []


class TrackShipmentResponse(OTOBaseModel):
    """Response model for shipment tracking.
    
    Args:
        success: Indicates if tracking was successful.
        tracking_url: Delivery company tracking URL.
        items: List of tracking items.
    """
    success: bool
    tracking_url: Optional[str] = Field(None, alias="trackingUrl")
    items: List[ShipmentTrackingItem] = []


# =============================================================================
# AWB (SHIPPING LABEL) MODELS
# =============================================================================

class PrintAWBResponse(OTOBaseModel):
    """Response model for AWB printing.
    
    Args:
        print_awb_url: URL to download/print the shipping label.
        delivery_company: Delivery company for the shipment.
        tracking_number: Tracking number on the label.
    """
    print_awb_url: Optional[str] = Field(None, alias="printAWBURL")
    delivery_company: Optional[str] = Field(None, alias="deliveryCompany")
    tracking_number: Optional[str] = Field(None, alias="trackingNumber")


# =============================================================================
# CARRIER/DELIVERY MODELS
# =============================================================================

class CheckOTODeliveryFeeRequest(OTOBaseModel):
    """Request model for checking OTO delivery fees.
    
    Args:
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        weight: Package weight in kg.
        height: Package height in cm (optional).
        width: Package width in cm (optional).
        length: Package length in cm (optional).
        origin_lat: Origin latitude for bullet delivery (optional).
        origin_lon: Origin longitude for bullet delivery (optional).
        destination_lat: Destination latitude for bullet delivery (optional).
        destination_lon: Destination longitude for bullet delivery (optional).
        for_reverse_shipment: Check for return shipment options (optional).
        currency: ISO 4217 currency code (optional).
        package_count: Number of packages (optional).
        total_due: COD amount (optional).
        service_type: Filter by service type (optional).
        delivery_type: Filter by delivery type (optional).
    """
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    weight: float
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    origin_lat: Optional[float] = Field(None, alias="originLat")
    origin_lon: Optional[float] = Field(None, alias="originLon")
    destination_lat: Optional[float] = Field(None, alias="destinationLat")
    destination_lon: Optional[float] = Field(None, alias="destinationLon")
    for_reverse_shipment: Optional[bool] = Field(None, alias="forReverseShipment")
    currency: Optional[str] = None
    package_count: Optional[int] = Field(None, alias="packageCount")
    total_due: Optional[float] = Field(None, alias="totalDue")
    service_type: Optional[ServiceType] = Field(None, alias="serviceType")
    delivery_type: Optional[DeliveryType] = Field(None, alias="deliveryType")


class DeliveryOption(OTOBaseModel):
    """Available delivery option from a carrier.
    
    Args:
        delivery_option_id: Unique identifier for this option.
        delivery_option_name: Display name for the option.
        delivery_company_name: Carrier name/code.
        service_type: Type of service (express, sameDay, etc.).
        delivery_type: How the package is delivered.
        price: Base delivery price.
        currency: Price currency.
        return_fee: Fee for return shipments.
        cod_charge: Cash on delivery fee.
        max_cod_value: Maximum COD amount allowed.
        max_order_value: Maximum order value allowed.
        max_free_weight: Weight included in base price.
        extra_weight_per_kg: Additional cost per kg over free weight.
        avg_delivery_time: Estimated delivery time.
        pickup_cutoff_time: Latest pickup time.
        logo: URL to carrier logo.
        pickup_dropoff: Pickup/dropoff availability.
        tracking_type: Quality of tracking (excellent, good, etc.).
        check_all_branches: URL to find carrier branches.
        card_on_delivery_percentage: Card payment fee description.
    """
    delivery_option_id: int = Field(alias="deliveryOptionId")
    delivery_option_name: str = Field(alias="deliveryOptionName")
    delivery_company_name: str = Field(alias="deliveryCompanyName")
    service_type: Optional[str] = Field(None, alias="serviceType")
    delivery_type: Optional[str] = Field(None, alias="deliveryType")
    price: float
    currency: str
    return_fee: Optional[float] = Field(None, alias="returnFee")
    cod_charge: Optional[float] = Field(None, alias="codCharge")
    max_cod_value: Optional[float] = Field(None, alias="maxCODValue")
    max_order_value: Optional[float] = Field(None, alias="maxOrderValue")
    max_free_weight: Optional[float] = Field(None, alias="maxFreeWeight")
    extra_weight_per_kg: Optional[float] = Field(None, alias="extraWeightPerKg")
    avg_delivery_time: Optional[str] = Field(None, alias="avgDeliveryTime")
    pickup_cutoff_time: Optional[str] = Field(None, alias="pickupCutOffTime")
    logo: Optional[str] = None
    pickup_dropoff: Optional[str] = Field(None, alias="pickupDropoff")
    tracking_type: Optional[str] = Field(None, alias="trackingType")
    check_all_branches: Optional[str] = Field(None, alias="checkAllBranches")
    card_on_delivery_percentage: Optional[str] = Field(None, alias="cardOnDeliveryPercentage")


class CheckDeliveryFeeResponse(OTOBaseModel):
    """Response model for delivery fee checks.
    
    Args:
        success: Indicates if the check was successful.
        delivery_company: List of available delivery options.
        trace_id: Request trace identifier for debugging.
    """
    success: bool
    delivery_company: List[DeliveryOption] = Field(default=[], alias="deliveryCompany")
    trace_id: Optional[str] = Field(None, alias="traceId")


class CheckDeliveryFeeRequest(OTOBaseModel):
    """Request model for checking contract-based delivery fees.
    
    Args:
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        weight: Package weight in kg.
        total_due: COD amount (optional).
        height: Package height in cm (optional).
        width: Package width in cm (optional).
        length: Package length in cm (optional).
        delivery_type: bullet or courier (optional).
        origin_lat: Origin latitude for bullet (optional).
        origin_lon: Origin longitude for bullet (optional).
        destination_lat: Destination latitude for bullet (optional).
        destination_lon: Destination longitude for bullet (optional).
    """
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    weight: float
    total_due: Optional[float] = Field(None, alias="totalDue")
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    delivery_type: Optional[str] = Field(None, alias="deliveryType")
    origin_lat: Optional[float] = Field(None, alias="originLat")
    origin_lon: Optional[float] = Field(None, alias="originLon")
    destination_lat: Optional[float] = Field(None, alias="destinationLat")
    destination_lon: Optional[float] = Field(None, alias="destinationLon")


class GetDeliveryFeeRequest(OTOBaseModel):
    """Request model for getting all delivery fees (OTO + contract).
    
    Args:
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        weight: Package weight in kg.
        total_due: COD amount (optional).
        height: Package height in cm (optional).
        width: Package width in cm (optional).
        length: Package length in cm (optional).
    """
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    weight: float
    total_due: Optional[float] = Field(None, alias="totalDue")
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None


class GetDeliveryEstimationRequest(OTOBaseModel):
    """Request model for delivery time estimation.
    
    Args:
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        delivery_option_id: Specific delivery option to estimate.
        district: District for district-based SLA (optional).
    """
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    delivery_option_id: int = Field(..., alias="deliveryOptionId")
    district: Optional[str] = None


class CheckCoverageRequest(OTOBaseModel):
    """Request model for checking delivery coverage.
    
    Args:
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        package_size: Package size category (optional).
    """
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    package_size: Optional[str] = Field(None, alias="packageSize")


class AvailableCitiesRequest(OTOBaseModel):
    """Request model for getting available cities.
    
    Args:
        delivery_option_id: Filter cities by delivery option.
        per_page: Results per page (max 100).
    """
    delivery_option_id: int = Field(..., alias="deliveryOptionId")
    per_page: Optional[int] = Field(None, alias="perPage")


class AvailableTimeSlotsRequest(OTOBaseModel):
    """Request model for getting available delivery time slots.
    
    Args:
        delivery_option_id: Delivery option to check slots for.
        origin_city: Pickup city name.
        destination_city: Delivery city name.
        package_size: Package size category (optional).
    """
    delivery_option_id: int = Field(..., alias="deliveryOptionId")
    origin_city: str = Field(..., alias="originCity")
    destination_city: str = Field(..., alias="destinationCity")
    package_size: Optional[str] = Field(None, alias="packageSize")


class GetCitiesRequest(OTOBaseModel):
    """Request model for getting city list.
    
    Args:
        country: ISO2 country code.
        per_page: Results per page (default 100, max 500).
        page: Page number for pagination.
    """
    country: str
    per_page: Optional[int] = Field(None, alias="perPage")
    page: Optional[int] = None


# =============================================================================
# PICKUP LOCATION MODELS
# =============================================================================

class CreatePickupLocationRequest(OTOBaseModel):
    """Request model for creating a pickup location.
    
    Args:
        name: Name of the pickup location.
        code: Unique code identifier for the location.
        mobile: Contact mobile number.
        city: City name.
        country: ISO2 country code.
        address: Full address.
        contact_name: Contact person's name.
        contact_email: Contact person's email.
        type: Location type (branch or warehouse).
        lat: Latitude coordinate (optional).
        lon: Longitude coordinate (optional).
        postcode: Postal code (optional).
        district: District name (optional).
        state: State/province (optional).
        street: Street name (optional).
        short_address_code: National address short code (optional).
        secondary_address_number: Secondary address number (optional).
        building_no: Building number (optional).
        serving_radius: Serving radius in km for branches (optional).
        brand_name: Associated brand name (optional).
        status: Location status (active/inactive) (optional).
    """
    name: str
    code: str
    mobile: str
    city: str
    country: str
    address: str
    contact_name: str = Field(..., alias="contactName")
    contact_email: str = Field(..., alias="contactEmail")
    type: Optional[PickupLocationType] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    postcode: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    street: Optional[str] = None
    short_address_code: Optional[str] = Field(None, alias="shortAddressCode")
    secondary_address_number: Optional[str] = Field(None, alias="secondaryAddressNumber")
    building_no: Optional[str] = Field(None, alias="buildingNo")
    serving_radius: Optional[float] = Field(None, alias="servingRadius")
    brand_name: Optional[str] = Field(None, alias="brandName")
    status: Optional[PickupLocationStatus] = None


class CreatePickupLocationResponse(OTOBaseModel):
    """Response model after creating a pickup location.
    
    Args:
        success: Indicates if creation was successful.
        warehouse_id: ID of the created warehouse.
        pickup_location_code: The location code.
        message: Status message.
    """
    success: bool
    warehouse_id: Optional[str] = Field(None, alias="warhouseId")
    pickup_location_code: Optional[str] = Field(None, alias="pickupLocationCode")
    message: Optional[str] = None


class UpdatePickupLocationRequest(OTOBaseModel):
    """Request model for updating a pickup location.
    
    Args:
        code: The location code to update (required).
        name: Updated name (optional).
        mobile: Updated mobile (optional).
        city: Updated city (optional).
        country: Updated country (optional).
        address: Updated address (optional).
        contact_name: Updated contact name (optional).
        contact_email: Updated contact email (optional).
        type: Updated type (optional).
        lat: Updated latitude (optional).
        lon: Updated longitude (optional).
        postcode: Updated postal code (optional).
        district: Updated district (optional).
        state: Updated state (optional).
        street: Updated street (optional).
        secondary_address_number: Updated secondary number (optional).
        building_no: Updated building number (optional).
        serving_radius: Updated serving radius (optional).
        brand_name: Updated brand name (optional).
        status: Updated status (optional).
    """
    code: str
    name: Optional[str] = None
    mobile: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = Field(None, alias="contactName")
    contact_email: Optional[str] = Field(None, alias="contactEmail")
    type: Optional[PickupLocationType] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    postcode: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    street: Optional[str] = None
    secondary_address_number: Optional[str] = Field(None, alias="secondaryAddressNumber")
    building_no: Optional[str] = Field(None, alias="buildingNo")
    serving_radius: Optional[float] = Field(None, alias="servingRadius")
    brand_name: Optional[str] = Field(None, alias="brandName")
    status: Optional[PickupLocationStatus] = None


class UpdatePickupLocationResponse(OTOBaseModel):
    """Response model after updating a pickup location.
    
    Args:
        success: Indicates if update was successful.
        branch_id: ID of the updated branch.
        pickup_location_code: The location code.
    """
    success: bool
    branch_id: Optional[str] = Field(None, alias="branchId")
    pickup_location_code: Optional[str] = Field(None, alias="pickupLocationCode")


class PickupLocation(OTOBaseModel):
    """Pickup location details.
    
    Args:
        id: Location identifier.
        code: Unique location code.
        name: Location name.
        address: Full address.
        city: City name.
        country: Country code.
        contact_person: Contact person's name.
        contact_phone: Contact phone number.
        contact_email: Contact email.
        lat: Latitude.
        lon: Longitude.
        district: District name.
        street: Street name.
        building_no: Building number.
        secondary_address_number: Secondary address number.
        short_address_code: Short address code.
        postcode: Postal code.
    """
    id: int
    code: str
    name: str
    address: str
    city: str
    country: Optional[str] = None
    contact_person: Optional[str] = Field(None, alias="contactPerson")
    contact_phone: Optional[str] = Field(None, alias="contactPhone")
    contact_email: Optional[str] = Field(None, alias="contactEmail")
    lat: Optional[float] = None
    lon: Optional[float] = None
    district: Optional[str] = None
    street: Optional[str] = None
    building_no: Optional[str] = Field(None, alias="buildingNo")
    secondary_address_number: Optional[str] = Field(None, alias="secondaryAddressNumber")
    short_address_code: Optional[str] = Field(None, alias="shortAddressCode")
    postcode: Optional[str] = None


class GetPickupLocationListResponse(OTOBaseModel):
    """Response model for pickup location list.
    
    Args:
        success: Indicates if request was successful.
        warehouses: List of warehouse locations.
        branches: List of branch locations.
    """
    success: bool
    warehouses: List[PickupLocation] = []
    branches: List[PickupLocation] = []


# =============================================================================
# BRAND MODELS
# =============================================================================

class Brand(OTOBaseModel):
    """Brand/client store information.
    
    Args:
        id: Brand identifier.
        company_id: Associated company ID.
        store_name: Brand/store name.
        warehouse_name: Default warehouse name.
        brand_logo: URL to brand logo.
        default_warehouse_id: Default warehouse ID.
    """
    id: int = Field(alias="ID")
    company_id: int = Field(alias="companyId")
    store_name: str = Field(alias="storeName")
    warehouse_name: Optional[str] = Field(None, alias="wareHouseName")
    brand_logo: Optional[str] = Field(None, alias="brandLogo")
    default_warehouse_id: Optional[int] = Field(None, alias="defaultWarehouseId")


class GetBrandListResponse(OTOBaseModel):
    """Response model for brand list.
    
    Args:
        success: Indicates if request was successful.
        client_stores: List of brands/client stores.
    """
    success: bool
    client_stores: List[Brand] = Field(default=[], alias="clientStores")


class StoreConfig(OTOBaseModel):
    """Store configuration for a brand.
    
    Args:
        store_name: Store display name.
        sales_channel_credentials_id: Associated sales channel credentials.
    """
    store_name: str = Field(alias="storeName")
    sales_channel_credentials_id: Optional[int] = Field(None, alias="salesChannelCredentialsID")


class CreateBrandRequest(OTOBaseModel):
    """Request model for creating a brand.
    
    Args:
        store_name: Name of the brand/store.
        logo: URL to brand logo (optional).
        default_warehouse_id: Default warehouse ID (optional).
        stores: List of store configurations (optional).
    """
    store_name: str = Field(..., alias="storeName")
    logo: Optional[str] = None
    default_warehouse_id: Optional[int] = Field(None, alias="defaultWarehouseID")
    stores: Optional[List[StoreConfig]] = None


class CreateBrandResponse(OTOBaseModel):
    """Response model after creating a brand.
    
    Args:
        success: Indicates if creation was successful.
        client_store_id: ID of the created brand.
    """
    success: bool
    client_store_id: Optional[int] = Field(None, alias="clientStoreId")


# =============================================================================
# PRODUCT MODELS
# =============================================================================

class CustomAttribute(OTOBaseModel):
    """Custom attribute for a product.
    
    Args:
        attribute_name: Name of the attribute.
        attribute_value: Value of the attribute.
    """
    attribute_name: str = Field(..., alias="attributeName")
    attribute_value: Optional[str] = Field(None, alias="attributeValue")


class CreateProductRequest(OTOBaseModel):
    """Request model for creating a product.
    
    Args:
        sku: Stock Keeping Unit identifier.
        product_name: Display name of the product.
        price: Product price.
        tax_amount: Tax amount (optional).
        brand_id: Associated brand ID (optional).
        description: Product description (optional).
        barcode: Primary barcode (optional).
        second_barcode: Secondary barcode (optional).
        product_image: URL to product image (optional).
        category: Product category (optional).
        hs_code: Harmonized System code for customs (optional).
        item_origin: Country of origin (optional).
        bundle_items: Whether product is a bundle (optional).
        packaging_material: Whether used for packaging (optional).
        custom_attributes: List of custom attributes (optional).
    """
    sku: str
    product_name: str = Field(..., alias="productName")
    price: str
    tax_amount: Optional[str] = Field(None, alias="taxAmount")
    brand_id: Optional[int] = Field(None, alias="brandId")
    description: Optional[str] = None
    barcode: Optional[str] = None
    second_barcode: Optional[str] = Field(None, alias="secondBarcode")
    product_image: Optional[str] = Field(None, alias="productImage")
    category: Optional[str] = None
    hs_code: Optional[str] = Field(None, alias="hsCode")
    item_origin: Optional[str] = Field(None, alias="itemOrigin")
    bundle_items: Optional[bool] = Field(None, alias="bundleItems")
    packaging_material: Optional[bool] = Field(None, alias="packagingMaterial")
    custom_attributes: Optional[List[CustomAttribute]] = Field(None, alias="customAttributes")


class CreateProductResponse(OTOBaseModel):
    """Response model after creating a product.
    
    Args:
        success: Indicates if creation was successful.
        product_id: ID of the created product.
    """
    success: bool
    product_id: Optional[int] = Field(None, alias="productId")


class Product(OTOBaseModel):
    """Product summary information.
    
    Args:
        name: Product name.
        sku: Stock Keeping Unit.
        barcode: Product barcode.
        product_image: URL to product image.
    """
    name: str
    sku: str
    barcode: Optional[str] = None
    product_image: Optional[str] = Field(None, alias="productImage")


class ProductListRequest(OTOBaseModel):
    """Request model for product list.
    
    Args:
        page_size: Number of products per page (default 100).
        current_page: Page number (default 1).
    """
    page_size: Optional[int] = Field(None, alias="pageSize")
    current_page: Optional[int] = Field(None, alias="currentPage")


class ProductListResponse(OTOBaseModel):
    """Response model for product list.
    
    Args:
        success: Indicates if request was successful.
        product_count: Total number of products.
        products: List of products.
    """
    success: bool
    product_count: Optional[int] = Field(None, alias="productCount")
    products: List[Product] = []


# =============================================================================
# BOX MODELS
# =============================================================================

class AddBoxRequest(OTOBaseModel):
    """Request model for adding a box type.
    
    Args:
        name: Unique name for the box type.
        length: Box length in cm.
        width: Box width in cm.
        height: Box height in cm.
    """
    name: str
    length: float
    width: float
    height: float


class AddBoxResponse(OTOBaseModel):
    """Response model after adding a box.
    
    Args:
        success: Indicates if creation was successful.
        message: Status message.
    """
    success: bool
    message: Optional[str] = None


class UpdateBoxRequest(OTOBaseModel):
    """Request model for updating a box type.
    
    Args:
        name: Name of the box to update.
        length: New length in cm.
        width: New width in cm.
        height: New height in cm.
    """
    name: str
    length: float
    width: float
    height: float


class Box(OTOBaseModel):
    """Box type information.
    
    Args:
        id: Box identifier.
        box_name: Box type name.
        length: Length in cm.
        width: Width in cm.
        height: Height in cm.
    """
    id: int
    box_name: str = Field(alias="boxName")
    length: float
    width: float
    height: float


class GetBoxResponse(OTOBaseModel):
    """Response model for box list.
    
    Args:
        success: Indicates if request was successful.
        boxes: List of box types.
    """
    success: bool
    boxes: List[Box] = []


# =============================================================================
# WEBHOOK MODELS
# =============================================================================

class WebhookRequest(OTOBaseModel):
    """Request model for webhook operations.
    
    Args:
        url: Webhook endpoint URL.
        method: HTTP method (POST or GET).
        secret_key: Secret key for webhook authentication (optional).
        events: List of events to subscribe to (optional).
    """
    url: str
    method: str = "POST"
    secret_key: Optional[str] = Field(None, alias="secretKey")
    events: Optional[List[str]] = None


class WebhookResponse(OTOBaseModel):
    """Response model for webhook operations.
    
    Args:
        success: Indicates if operation was successful.
        message: Status message.
    """
    success: bool
    message: Optional[str] = None


# =============================================================================
# STOCK MANAGEMENT MODELS
# =============================================================================

class UpdateStockQuantityRequest(OTOBaseModel):
    """Request model for updating stock quantity.
    
    Args:
        sku: Product SKU to update.
        quantity: New quantity or quantity change.
        action_type: How to apply the quantity (set, increment, decrement).
        warehouse_code: Warehouse to update (optional).
    """
    sku: str
    quantity: int
    action_type: str = Field(..., alias="actionType")
    warehouse_code: Optional[str] = Field(None, alias="warehouseCode")


class UpdateStockQuantityResponse(OTOBaseModel):
    """Response model after updating stock.
    
    Args:
        success: Indicates if update was successful.
        transaction_id: Transaction identifier.
        warnings: List of warning messages.
    """
    success: bool
    transaction_id: Optional[int] = Field(None, alias="transactionID")
    warnings: List[str] = []


# =============================================================================
# GENERIC RESPONSE MODELS
# =============================================================================

class SuccessResponse(OTOBaseModel):
    """Generic success response.
    
    Args:
        success: Indicates if the operation was successful.
        message: Optional status message.
    """
    success: bool
    message: Optional[str] = None


class ErrorResponse(OTOBaseModel):
    """Generic error response from OTO API.
    
    Args:
        success: Always False for errors.
        oto_error_code: OTO-specific error code.
        oto_error_message: Human-readable error message.
    """
    success: bool = False
    oto_error_code: Optional[str] = Field(None, alias="otoErrorCode")
    oto_error_message: Optional[str] = Field(None, alias="otoErrorMessage")
