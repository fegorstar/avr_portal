from rest_framework.response import Response
from rest_framework import status


def success_response(message, data=None, count=None, status_code=status.HTTP_200_OK):
    """
    Generate a standardized success response with optional count.

    Args:
    - message (str): The success message.
    - data (dict): Optional data to include in the response.
    - count (int): Optional count of items.
    - status_code (int): The HTTP status code for the response.

    Returns:
    - Response: A DRF Response object with the standardized format.
    """
    response_data = {
        "status": status_code,
        "message": message
    }
    if count is not None:
        response_data['count'] = count
    response_data['data'] = data if data else {}

    return Response(response_data, status=status_code)


def error_response(message, validation_errors=None, error_type=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Generate a standardized error response with optional validation errors and error type.

    Args:
    - message (str): The error message.
    - validation_errors (dict): Optional dictionary of validation errors.
    - error_type (str): Optional type of the error.
    - status_code (int): The HTTP status code for the response.

    Returns:
    - Response: A DRF Response object with the standardized format.
    """
    response_data = {
        "status": status_code,
        "message": message,
    }
    if validation_errors:
        response_data['errors'] = validation_errors
    if error_type:
        response_data['error_type'] = error_type
    return Response(response_data, status=status_code)
