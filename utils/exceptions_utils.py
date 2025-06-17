from rest_framework.exceptions import APIException
from rest_framework import exceptions, status


class CustomException(exceptions.APIException):
    # Default HTTP status code for the exception
    default_status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail=None, status_code=None):
        # Call the superclass's __init__ method
        super().__init__(detail=None)

        # Set the detail attribute to an empty dictionary if not provided
        if detail is not None:
            self.detail = {'error': detail}

        # Set the status_code attribute to provided status_code or default if not provided
        if status_code is not None:
            self.status_code = status_code
        else:
            self.status_code = self.default_status_code

    def get_full_details(self):
        # Return a dictionary with the status code and the error detail
        return {
            'status_code': self.status_code,
            # Access the 'error' key in the detail dictionary
            'error': self.detail['error']
        }
