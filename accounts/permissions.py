from rest_framework.permissions import BasePermission
from .exceptions import CustomException
from accounts.models import User


class IsUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (request.user.role in [User.STAFF, User.AGENT, User.CLIENT])
        )


# class IsAdminOrTutor(BasePermission):
#     def has_permission(self, request, view):
#         return (
#             request.user.is_authenticated
#             and request.user.is_verified
#             and (request.user.user_type in ['ADMIN', 'TUTOR'])
#         )


# class IsSuperAdmin(BasePermission):
#     def has_permission(self, request, view):
#         if not request.user.is_authenticated:
#             raise CustomException(
#                 detail='You do not have permission to perform this action.')

#         # Check if the user is a super admin and ADMIN
#         if request.user.user_type == 'ADMIN' or request.user.is_superuser:
#             return True

#         raise CustomException(
#             detail='You do not have permission to perform this action.')
