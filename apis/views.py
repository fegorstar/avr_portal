from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status, generics
import math
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import permissions
from utils.response_utils import success_response, error_response  # Import the response utils
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from staffs.models import Client, Agent, Job, Report
from django.db.models import Q
from staffs.filters import JobFilter, ReportFilter
from django.urls import reverse
from .serializers import JobSerializer, ReportSerializer
from django.db import transaction
###################### JOB/REPORTS RETRIEVAL API ###########################################
################# JobCreateView ####################################

class JobCreateView(generics.GenericAPIView):
    serializer_class = JobSerializer

    @swagger_auto_schema(
        tags=["Jobs"],
        operation_summary="Create new jobs for a specific client",
        operation_description="Create multiple job records for a specific client ID. The request should contain a list of job records.",
        request_body=JobSerializer(many=True),
        responses={
            201: "Jobs created successfully.",
            400: "Bad request. Check the request payload."
        }
    )
    def post(self, request, client_id=None, *args, **kwargs):
        # Ensure client_id is provided
        if not client_id:
            return error_response(
                message="Client ID is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate the request data
        data = request.data
        if not isinstance(data, list):
            return error_response(
                message="A list of job records is expected.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Add client_id to each job record
        for job in data:
            job['client'] = client_id

        serializer = self.serializer_class(data=data, many=True)
        
        if not serializer.is_valid():
            return error_response(
                message="Validation errors occurred.",
                validation_errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Using transaction for bulk creation
        try:
            with transaction.atomic():
                jobs = Job.objects.bulk_create([
                    Job(**job_data) for job_data in serializer.validated_data
                ])
        except Exception as e:
            return error_response(
                message=f"Failed to create jobs due to an error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return success_response(
            message="Jobs created successfully.",
            data={"jobs": JobSerializer(jobs, many=True).data},
            status_code=status.HTTP_201_CREATED
        )
###########################################################################################
######################### JobListView ################################################

class JobListView(APIView):
    serializer_class = JobSerializer
    pagination_class = PageNumberPagination  # Specify the pagination class

    @swagger_auto_schema(
        tags=["Jobs"],
        operation_summary="Get jobs for a specific client",
        operation_description="Retrieve all jobs associated with a given client ID. Supports filtering and pagination.",
        responses={
            200: "Jobs retrieved successfully.",
            404: "Jobs with the specified client ID not found."
        }
    )
    def get(self, request, client_id=None, format=None):
        # Ensure client_id is provided
        if not client_id:
            return error_response(
                message="Client ID is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve the queryset based on client_id
        job_queryset = Job.objects.filter(client_id=client_id).select_related('client').order_by('-created_at')

        # Check if the queryset exists
        if not job_queryset.exists():
            return error_response(
                message=f"Jobs with Client ID: {client_id} not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Apply filtering using JobFilter (ensure filtering fields are indexed for performance)
        filterset = JobFilter(request.GET, queryset=job_queryset)
        filtered_qs = filterset.qs

        # Paginate the filtered queryset
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(filtered_qs, request, view=self)

        # Serialize the paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Return paginated response with success message
        return paginator.get_paginated_response({
            "message": "Jobs retrieved successfully.",
            "jobs": serializer.data
        })


#####################################################################################################

######################  AllReportsView ################################
class RetrieveAllReportsAPIView(APIView):
    serializer_class = ReportSerializer
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        tags=["Reports"],
        operation_summary="Retrieve all reports",
        operation_description="Fetches all reports with pagination support.",
        responses={
            200: openapi.Response(
                description="Reports retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'data': ReportSerializer(many=True).to_representation({})
                    }
                )
            ),
            404: openapi.Response(
                description="No reports found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def get(self, request, format=None):
        # Efficiently fetch all reports with related data
        report_queryset = Report.objects.all().select_related('customer', 'approvedBy').order_by('-created_at')

        # Check if there are any reports
        if not report_queryset.exists():
            return Response(
                data={
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': "No reports found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Implement pagination
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(report_queryset, request, view=self)

        # Serialize paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Efficiently count the number of reports (if required)
        total_count = report_queryset.count()

        # Return paginated response
        return paginator.get_paginated_response({
            'status': status.HTTP_200_OK,
            'message': "Reports retrieved successfully.",
            'count': total_count,
            'data': serializer.data
        })

################################################################################


################## AllJobsView #################################################
class AllJobsView(APIView):
    serializer_class = JobSerializer
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        tags=["Jobs"],
        operation_summary="Retrieve all jobs",
        operation_description="Fetches all jobs with pagination support.",
        responses={
            200: openapi.Response(
                description="All jobs retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'data': JobSerializer(many=True).to_representation({})
                    }
                )
            ),
            404: openapi.Response(
                description="No jobs found.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def get(self, request, format=None):
        # Efficiently fetch all jobs and related data
        job_queryset = Job.objects.all().select_related('client', 'agent').order_by('-created_at')

        # Check if there are any jobs available
        if not job_queryset.exists():
            return Response(
                data={
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': "No jobs found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Paginate the queryset
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(job_queryset, request, view=self)

        # Serialize paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Count total jobs (if needed)
        total_count = job_queryset.count()

        # Return paginated response
        return paginator.get_paginated_response({
            'status': 200,
            'message': "All jobs retrieved successfully.",
            'count': total_count,
            'data': serializer.data
        })
##########################################################################################

#################### JobsByStatusView ###############################################
class JobsByStatusView(APIView):
    serializer_class = JobSerializer
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        tags=["Jobs"],
        operation_summary="Retrieve jobs by status",
        operation_description="Fetches jobs based on their status code with pagination support.",
        manual_parameters=[
            openapi.Parameter(
                'status_code', openapi.IN_PATH,
                description="Status code to filter jobs",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Jobs by status retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'data': JobSerializer(many=True).to_representation({})
                    }
                )
            ),
            404: openapi.Response(
                description="No jobs found with the specified status code.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def get(self, request, status_code=None, format=None):
        # Optimize by using select_related for foreign keys (e.g., client, agent)
        job_queryset = Job.objects.filter(status=status_code).select_related('client', 'agent').order_by('-created_at')

        # Check if there are any jobs with the given status
        if not job_queryset.exists():
            return Response(
                {
                    'status': status.HTTP_404_NOT_FOUND,
                    'message': f"Jobs with Status: {status_code} not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Apply pagination
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(job_queryset, request, view=self)

        # Serialize the paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Count total jobs
        total_count = job_queryset.count()

        # Return paginated response
        return paginator.get_paginated_response({
            'status': status.HTTP_200_OK,
            'message': "Jobs by status retrieved successfully.",
            'count': total_count,
            'data': serializer.data
        })
######################################################################################
############ ClientReportsView ###########################################
class ClientReportsView(APIView):
    serializer_class = ReportSerializer
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        tags=["Reports"],
        operation_summary="Retrieve client-specific reports",
        operation_description="Fetches reports for a specific client using the client_id with pagination support.",
        manual_parameters=[
            openapi.Parameter(
                'client_id', openapi.IN_PATH,
                description="Client ID to filter reports",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Client reports retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'data': ReportSerializer(many=True).to_representation({})
                    }
                )
            ),
            404: openapi.Response(
                description="No reports found for the specified client.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def get(self, request, client_id=None, format=None):
        # Optimize the query by using select_related to reduce database hits
        report_queryset = Report.objects.filter(
            customer__client_id=client_id
        ).select_related('customer', 'customer__client').order_by('-created_at')

        # Check if any reports are found
        if not report_queryset.exists():
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": f"Reports for Client ID: {client_id} not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Paginate the results
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(report_queryset, request, view=self)

        # Serialize the paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Pass the paginated response with serialized data
        return paginator.get_paginated_response({
            "status": status.HTTP_200_OK,
            "message": "Client reports retrieved successfully.",
            "count": len(paginated_qs),  # Use the length of the paginated queryset
            "data": serializer.data
        })

###############################################################################################

################## ReportsByStatusView ####################################################
class ReportsByStatusView(APIView):
    serializer_class = ReportSerializer
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        tags=["Reports"],
        operation_summary="Retrieve reports by status",
        operation_description="Fetches reports based on their status code with pagination support.",
        manual_parameters=[
            openapi.Parameter(
                'status_code', openapi.IN_PATH,
                description="Status code to filter reports",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Reports by status retrieved successfully.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'data': ReportSerializer(many=True).to_representation({})
                    }
                )
            ),
            404: openapi.Response(
                description="No reports found with the specified status code.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def get(self, request, status_code=None, format=None):
        # Optimize query with select_related if applicable
        report_queryset = Report.objects.filter(Reportstatus=status_code).order_by('-created_at')

        if not report_queryset.exists():
            return Response(
                {
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": f"Reports with Status: {status_code} not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # Paginate the results
        paginator = self.pagination_class()
        paginated_qs = paginator.paginate_queryset(report_queryset, request, view=self)

        # Serialize the paginated data
        serializer = self.serializer_class(paginated_qs, many=True)

        # Pass the paginated response with serialized data and avoid extra .count() query
        return paginator.get_paginated_response({
            "status": status.HTTP_200_OK,
            "message": "Reports by status retrieved successfully.",
            "count": len(paginated_qs),  # Use the length of the paginated queryset
            "data": serializer.data
        })


###################################################################################