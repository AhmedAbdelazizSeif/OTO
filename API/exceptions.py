"""
Custom exceptions for OTO API errors.

This module defines a hierarchy of exceptions that can be raised when
interacting with the OTO API, enabling structured error handling.
"""

from typing import Optional


class OTOException(Exception):
    """Base exception for all OTO API errors.
    
    Args:
        message: Human-readable error message.
        status_code: HTTP status code from the response, if available.
        error_code: OTO-specific error code (e.g., 'OTO1001').
        error_message: OTO-specific error message from the API response.
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(self.message)
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.error_code:
            parts.append(f"Code: {self.error_code}")
        if self.error_message:
            parts.append(f"Detail: {self.error_message}")
        return " | ".join(parts)


class OTOAuthenticationError(OTOException):
    """Raised when authentication fails (401 Unauthorized).
    
    This typically occurs when the access token is expired, invalid,
    or missing from the request.
    """
    pass


class OTOAuthorizationError(OTOException):
    """Raised when the user lacks permission for an action (403 Forbidden).
    
    This occurs when the authenticated user doesn't have the required
    package or permissions for the requested endpoint.
    """
    pass


class OTONotFoundError(OTOException):
    """Raised when a requested resource is not found (404 Not Found).
    
    This typically occurs when an order, shipment, or other entity
    does not exist with the provided identifier.
    """
    pass


class OTOValidationError(OTOException):
    """Raised when request validation fails (400 Bad Request).
    
    This occurs when required fields are missing, have invalid formats,
    or contain values outside acceptable ranges.
    """
    pass


class OTOConflictError(OTOException):
    """Raised when there's a conflict with the current state (409 Conflict).
    
    This typically occurs when trying to perform an action that conflicts
    with the current state of a resource (e.g., canceling an already
    picked up shipment).
    """
    pass


class OTORateLimitError(OTOException):
    """Raised when API rate limits are exceeded (429 Too Many Requests).
    
    This occurs when too many requests are made in a short period.
    Implement exponential backoff when handling this exception.
    """
    pass


class OTOServerError(OTOException):
    """Raised when the OTO server encounters an error (5xx errors).
    
    This indicates a problem on OTO's side. Retry the request after
    a brief delay.
    """
    pass


class OTOInsufficientCreditError(OTOException):
    """Raised when account credit is insufficient for an operation.
    
    This occurs when trying to create a shipment but the account
    doesn't have enough credit balance.
    """
    pass


class OTONetworkError(OTOException):
    """Raised when a network-level error occurs.
    
    This includes connection timeouts, DNS failures, and other
    transport-level issues.
    """
    pass
