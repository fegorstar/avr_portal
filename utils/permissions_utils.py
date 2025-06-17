from rest_framework.permissions import BasePermission
from rest_framework import status


class IsUser(BasePermission):
    def has_permission(self, request, view):
        if (request.user.is_authenticated and
            request.user.is_verified and
                request.user.user_type in ['STUDENT', 'TUTOR', 'ADMIN']):
            return True

        return False


class IsOwnerOrAdminOrTutor(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.user == request.user:
            return True
        if request.user.user_type in ['ADMIN', 'TUTOR']:
            return True
        return False


class IsAdminOrTutor(BasePermission):
    def has_permission(self, request, view):
        if (request.user.is_authenticated and
            request.user.is_verified and
                request.user.user_type in ['ADMIN', 'TUTOR']):
            return True

        return False


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.user_type == 'ADMIN' or request.user.is_superuser:
            return True

        return False
