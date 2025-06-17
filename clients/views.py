from django.db import transaction
from django.db.models import Count  # Import Count
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.timesince import timesince
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User, UserProfile
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_client

from accounts.forms import UserProfileForm, UserForm, UserProfileUpdateForm
from .forms import ClientuserForm, ClientForm, clientJobForm, PublishJobForm, ClientEditJobForm
from staffs.forms import JobForm, ImportForm, uploadJobForm, EditJobForm, ReportJobForm, EditReportForm, UpdateReportForm
from django.contrib import messages, auth
from staffs.models import Client, Agent, Job, Report
from django.http import HttpResponse
import requests
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from staffs.filters import JobFilter, ReportFilter
from django.urls import reverse
from utils.response_utils import success_response, error_response  # Import the response utils
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
# Libraries For the bulk Job uploads
from django.views.generic.base import View
from csv import DictReader
from io import TextIOWrapper
from django.views.decorators.http import require_POST


# Import PDF Stuff
from django.http import FileResponse
import io
from reportlab.lib.units import inch
from io import BytesIO
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.pagesizes import A4
from datetime import datetime
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from dateutil import parser
from django.utils import timezone
import datetime
from datetime import datetime
from rest_framework.response import Response
from rest_framework import status, generics
import math
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import permissions


# ================================ CLient View Jobs===============================================

@login_required(login_url='login')
@user_passes_test(check_role_client)
def jobs(request):
    # To show loggedin Userprofile - who is adding the job
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    client = get_object_or_404(Client, user=request.user)

    # query only client jobs
    # Create an instance of the JobFilter
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(client=client).all().order_by('-created_at'))
    total_no_of_jobs = Job.objects.filter(client=client).all().count()

    context = {
        'total_no_of_jobs': total_no_of_jobs,
        'profile': profile,
        'my_Filter': job_filter,  # Use the correct variable name
        'client': client  # can access contactdetails and profile from here
    }
    return render(request, 'clients/jobs/jobs.html', context)


# --------------FETCH JOB DATA INTO THE DATATABLE IN JOBS PAGE###


@login_required(login_url='login')
@user_passes_test(check_role_client)
def fetchclientjob_data(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')
    client = get_object_or_404(Client, user=request.user)

    # Initialize the JobFilter with request GET data
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(client=client).all().order_by('-created_at'))
    data = job_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['ref_no', 'clientJobrefID', 'first_name', 'last_name', 'address',
                   'state', 'city', 'client__client_name', 'created_at', 'agent__fullname']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        if ' ' in search_value:
            first_name, last_name = search_value.split(' ', 1)
            search_filter |= (Q(first_name__icontains=first_name)
                              & Q(last_name__icontains=last_name))
        data = data.filter(search_filter)

    records_total = Job.objects.count()
    records_filtered = data.count()

    paginator = Paginator(data, length)
    page_number = (start // length) + 1
    data_page = paginator.page(page_number)

    data = [
        {
            'id': item.id,
            'clientJobrefID': item.clientJobrefID,
            'customerName': f"{item.first_name or 'N/A'} {item.last_name or 'N/A'}",
            'address': item.address if item.address else 'N/A',
            'state': item.state if item.state else 'N/A',
            'city': item.city if item.city else 'N/A',
            'client': item.client.client_name if item.client else 'N/A',
            'agent': item.agent.fullname if item.agent and hasattr(item.agent, 'fullname') else 'N/A',
            'created_at': timezone.localtime(item.created_at).strftime('%Y-%m-%d %I:%M:%S %p') if item.created_at else 'N/A',
            'whenAssigned': timesince(item.whenAssigned) if item.whenAssigned else 'N/A',
        }
        for item in data_page
    ]

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }

    return JsonResponse(response)
# Adding job (CRUD for Jobs)  --best way of CRUD -using htmx


# ------------------View for rendering the edit job form---------------------
@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientedit_job_details(request):
    if request.method == 'GET':
        job_id = request.GET.get('id')
        job = get_object_or_404(Job, id=job_id)
        data = {
            'id': job.pk,
            'first_name': job.first_name,
            'last_name': job.last_name,
            'phone_number': job.phone_number,
            'email': job.email,
            'state': job.state,
            'city': job.city,
            'BATCH_NO': job.BATCH_NO,
            'address': job.address,
            'status': job.status,
            'published': job.published,
            # Add other fields as needed
        }
        return JsonResponse(data)
# ------------------end View for rendering the edit job form---------------------


# ====================View for updating job details for client=============================
@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientupdate_job(request):
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        job = get_object_or_404(Job, id=job_id)
        form = EditJobForm(request.POST, instance=job)

        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Job updated successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid form data'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})
# ====================end of View for updating job details=============================


# ------------------------delete single and bulk jobs--------------------------
@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientdelete_job(request):
    if request.method == 'POST':
        selected_ids = request.POST.getlist('ids[]')
        try:
            Job.objects.filter(id__in=selected_ids).delete()
            # Perform the delete action on selected IDs here
            # If successful, you can return a success response
            return JsonResponse({'success': True})
        except Job.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'One or more records not found.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
# ------------------------end of delete single and bulk jobs--------------------------


@login_required(login_url='login')
@user_passes_test(check_role_client)
def addjob(request):
    client = get_object_or_404(Client, user=request.user)
    form = clientJobForm(request=request, user=request.user)

    if request.method == "POST":
        form = clientJobForm(
            request=request, user=request.user, data=request.POST)

        if form.is_valid():
            job = form.save(commit=False)

            # If clientJobrefID is empty, update it with ref_no
            if not job.clientJobrefID:
                job.clientJobrefID = job.ref_no

            # Set other job details
            job.created_by = request.user
            job.status = 0  # set job to be pending
            job.save()

            response = HttpResponse(
                status=204,
                headers={
                    'HX-Trigger': json.dumps({
                        "jobListChanged": None,
                        "showMessage": "Job was added Successfully!",
                    })
                })
            response["HX-Redirect"] = reverse("clientjobs")
            return response

    else:
        form = clientJobForm(
            request=request, user=request.user, instance=client)

    context = {
        'form': form,
        'client': client  # can access contact details and profile from here
    }

    return render(request, 'clients/jobs/job_form.html', context)

# publish job , make it avaaible for verification


@login_required(login_url='login')
@user_passes_test(check_role_client)
def publishjob(request, pk):
    selected_job = get_object_or_404(Job, pk=pk)

    if request.method == "POST":
        jobform = PublishJobForm(request.POST, instance=selected_job)
        if jobform.is_valid():
            publishjob = jobform.save(commit=False)  # prepare to store
            publishjob.save()

            response = HttpResponse(
                status=204,
                headers={
                    'HX-Trigger': json.dumps({
                        "jobListChanged": None,
                        "showMessage": "This Job was Successfully Published!"
                    })


                })

        response["HX-Redirect"] = reverse("clientjobs")
        return response

    else:
        jobform = PublishJobForm(instance=selected_job)
        context = {
            'jobform': jobform,
            'selected_job': selected_job,
        }
    return render(request, 'clients/jobs/publishJobform.html', context)


# uploading bulk jobs
class ClientImportView(View):
    def get(self, request, *args, **kwargs):
        # prevent access to the page if not a client
        loggedinuser = request.user
        loggedinuser.role = User.CLIENT
        if request.user.is_authenticated and loggedinuser:
            context = {
                "form": ImportForm(),
            }
            return render(request, 'clients/jobs/jobupload.html', context)
        else:
            return redirect('login')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            jobs_file = request.FILES["jobs_file"]
            rows = TextIOWrapper(jobs_file, encoding='unicode_escape', newline="")
            row_count = 0
            new_jobs_count = 0
            skipped_jobs_count = 0
            form_errors = []  # Collecting validation errors

            new_jobs = []  # List to store new job objects for bulk create
            existing_job_ids = set()  # Set to store existing job identifiers (for efficient checking)
            current_user = request.user

            # Read and prepare all the rows in one go
            rows_data = list(DictReader(rows))

            # Collect all existing job references in one query
            client_jobref_ids = {row.get('clientJobrefID', '').strip().lower() for row in rows_data}
            address_first_last_name_pairs = {
                (row.get('address', '').strip().lower(),
                 row.get('first_name', '').strip().lower(),
                 row.get('last_name', '').strip().lower()) for row in rows_data}

            existing_jobs = Job.objects.filter(
                Q(clientJobrefID__in=client_jobref_ids) | 
                Q(address__in=[item[0] for item in address_first_last_name_pairs], 
                  first_name__in=[item[1] for item in address_first_last_name_pairs], 
                  last_name__in=[item[2] for item in address_first_last_name_pairs])
            )

            # Store the existing job identifiers
            existing_job_ids = set(existing_jobs.values_list('clientJobrefID', flat=True))

            for row in rows_data:
                row_count += 1

                # Skip empty rows
                if not any(row.values()):
                    continue

                clientJobrefID = row.get('clientJobrefID', '').strip().lower()
                address = row.get('address', '').strip().lower()
                first_name = row.get('first_name', '').strip().lower()
                last_name = row.get('last_name', '').strip().lower()

                # Check if job with this clientJobrefID exists in existing jobs
                if clientJobrefID in existing_job_ids or (address, first_name, last_name) in existing_job_ids:
                    skipped_jobs_count += 1
                    continue

                # If not, create new job
                form = uploadJobForm(row)
                if form.is_valid():
                    job = form.save(commit=False)
                    job.created_by = current_user  # Set created_by to current user

                    # If clientJobrefID is empty, use ref_no
                    if not job.clientJobrefID:
                        job.clientJobrefID = job.ref_no

                    new_jobs.append(job)
                else:
                    # Collect errors for each invalid row and associate with row number
                    form_errors.append({
                        'row': row_count,
                        'errors': form.errors
                    })

            # Bulk insert the new jobs
            if new_jobs:
                Job.objects.bulk_create(new_jobs)
                new_jobs_count = len(new_jobs)

            context = {
                "form": ImportForm(),
                "form_errors": form_errors,
                "row_count": row_count,
                "new_jobs_count": new_jobs_count,
                "skipped_jobs_count": skipped_jobs_count,
            }

            return render(request, 'clients/jobs/jobupload.html', context)

        except IntegrityError:
            transaction.set_rollback(True)
            form_errors.append({"IntegrityError": "Bulk insertion failed due to integrity error."})

            context = {
                "form": ImportForm(),
                "form_errors": form_errors,
                "row_count": row_count,
                "new_jobs_count": new_jobs_count,
                "skipped_jobs_count": skipped_jobs_count,
            }

            return render(request, 'clients/jobs/jobupload.html', context)

# =========================SCRIPT TO remove_duplicate_jobs========================


def remove_duplicate_providus_jobs(request):
    # Filter jobs where client name is "Wema"
    providus_jobs = Job.objects.filter(client__client_name="Providus")

    # Group providus jobs by first_name, last_name, and address
    duplicate_jobs = providus_jobs.values('first_name', 'last_name', 'address').annotate(
        count=Count('id')).filter(count__gt=1)

    # Get the total count of duplicate jobs removed
    total_removed_count = duplicate_jobs.count()

    for group in duplicate_jobs:
        first_name = group['first_name']
        last_name = group['last_name']
        address = group['address']
        duplicate_queryset = providus_jobs.filter(
            first_name=first_name, last_name=last_name, address=address)
        # Keep the first job (you can choose any logic here)
        job_to_keep = duplicate_queryset.first()
        duplicate_queryset.exclude(pk=job_to_keep.pk).delete()

    return render(request, 'clients/jobs/duplicate_providus_jobs_removed.html', {'duplicate_jobs_count': total_removed_count})

# =======================================Reports=================================
# ------------------client reports-------------------------


@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientapprovedreports(request):
    # To show loggedin Userprofile - who is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    client = get_object_or_404(Client, user=request.user)

    # Create an instance of the ReportFilter
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Client=client, Reportstatus=1).order_by('-created_at'))

    total_no_of_clientreports = report_filter.qs.count()

    context = {
        'profile': profile,
        'client': client,
        'total_no_of_clientreports': total_no_of_clientreports,
        'my_Filter': report_filter,
    }
    return render(request, 'clients/reports/allclientreports.html', context)


# =====================================fetch_clientreportdata===========================
@login_required(login_url='login')
@user_passes_test(check_role_client)
def fetch_clientreportdata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    client = get_object_or_404(Client, user=request.user)

    # Initialize the ReportFilter with request GET data
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Client=client, Reportstatus=1).order_by('-created_at'))
    data = report_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus', 'buildingCondition', 'buildingColor', 'buildingType',
                   'VerificationMessage', 'TAT', 'agent', 'created_at']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        data = data.filter(search_filter)

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

    records_total = data.count()
    records_filtered = data.count()

    paginator = Paginator(data, length)
    page_number = (start // length) + 1
    data_page = paginator.page(page_number)

    data = []

    for item in data_page:
        # Determine VerificationStatus
        verification_status = 'N/A'
        if item.VerificationMessage == 'Incomplete Information':
            verification_status = 'No - No'
        elif item.VerificationMessage == 'No Response at the Address':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Address Does Not Exist':
            verification_status = 'No - No'
        elif item.VerificationMessage == 'Security Agents prevented access to Address':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Address is an empty plot of Land':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'The Customer has relocated':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'The Customer is not known at the address':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'The Customer is known but does not reside in the premises':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Address exists and customer is known':
            verification_status = 'Yes - Yes'
        elif item.VerificationMessage == 'Customer does not live at the address but visits often':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'The Customer is deceased':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Could not locate address':
            verification_status = 'No - No'
        elif item.VerificationMessage == 'The Customer works at the address but does not reside there':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Customer was met at a different house number':
            verification_status = 'No - No'
        elif item.VerificationMessage == 'Address is customers family house and does not reside there':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Company is not known at the address':
            verification_status = 'Yes - No'
        elif item.VerificationMessage == 'Incomplete address':
            verification_status = 'No - No'
        elif item.VerificationMessage == 'Company is known and operate from the address':
            verification_status = 'Yes - Yes'
        # Add more cases as needed

        # Color-coded Reportstatus
        if item.Reportstatus == '0':
            report_status = '<span class="badge badge-warning">Pending</span>'
        elif item.Reportstatus == '1':
            report_status = '<span class="badge badge-primary">Approved</span>'
        elif item.Reportstatus == '2':
            report_status = '<span class="badge badge-danger">Rejected</span>'
        else:
            report_status = '<span class="badge badge-warning">Pending</span>'

        data.append({
            'id': item.id,
            'clientJobrefID': item.clientJobrefID,
            'customerName': f"{item.customerName  or 'N/A'}",
            'address': item.address if item.address else 'N/A',
            'client': item.Client if item.Client else 'N/A',
            'agent': item.agent if item.agent else 'N/A',
            'VerificationMessage': item.VerificationMessage if item.VerificationMessage else 'N/A',
            'VerificationStatus': verification_status,
            'Reportstatus': report_status,

            'TAT': item.TAT if item.TAT else 'N/A',
            'created_at': timezone.localtime(item.created_at).strftime('%Y-%m-%d %I:%M:%S %p') if item.created_at else 'N/A',
        })

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }

    return JsonResponse(response)


# Client Profile
@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    clientContactDetails = User.objects.get(
        email__exact=request.user)
    client = get_object_or_404(Client, user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=profile)
        user_form = ClientuserForm(
            request.POST,  request.FILES, instance=clientContactDetails)

        client_form = ClientForm(
            request.POST,  request.FILES, instance=client)

        if profile_form.is_valid() and user_form.is_valid() and client_form.is_valid():
            profile_form.save()
            user_form.save()
            client_form.save()
            messages.success(request, 'Account Profile Details was updated.')
            return redirect('clientprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)
            print(client_form.errors)

    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserProfileUpdateForm(instance=clientContactDetails)
        client_form = ClientForm(instance=client)

    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'client_form': client_form,
        'client': client  # can access contactdetails and profile from here

    }
    return render(request, 'clients/profile.html', context)

