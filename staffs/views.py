# Django Views and Utilities
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic.base import View
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.timesince import timesince
from django.utils import timezone
from django.conf import settings  # Import Django settings
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
# Django Models and Database
from django.db import transaction, models
from django.db.models import Q, F, Value, Count, ExpressionWrapper, fields
from django.db.models.functions import TruncMonth, Concat
from django.db.utils import IntegrityError
from django.core import serializers

# Forms and Models
from .forms import (CSVUploadForm, JobForm, AssignForm, EditJobForm, ImportForm, 
                    uploadJobForm, ImportReportForm, uploadReportForm, 
                    ReportJobForm, EditReportForm, UpdateReportForm)
from accounts.models import User, UserProfile
from accounts.forms import UserProfileForm, UserForm, UserProfileUpdateForm
from clients.forms import ClientForm
from agents.forms import AgentForm
from .models import Client, Agent, Job, Report
from accounts.views import check_role_staff
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages, auth

# External Libraries
import re
import csv
import json
import requests
from io import TextIOWrapper, BytesIO
from dateutil import parser
from datetime import datetime, timedelta
from csv import DictReader 

# ReportLab for PDF Generation
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

# Filters
from .filters import JobFilter, ReportFilter

# =========================================VIEW ALL JOBS SECTION===============================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def jobs(request):
    # To show loggedin Userprofile - who is adding the job
    profile = get_object_or_404(UserProfile, user=request.user)
    # query all jobs but only those published by clients
    Total_jobs = Job.objects.filter(published=1).all().count()

    # Create an instance of the JobFilter
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(published=1).all())

    context = {
        'Total_jobs': Total_jobs,
        'profile': profile,
        'my_Filter': job_filter,  # Use the correct variable name
        "form": AssignForm(),  # this is for bulkassign so that the form will appear on modal
    }
    return render(request, 'staffs/jobs/alljobs.html', context)


# ----------------------FETCH JOB DATA INTO THE DATATABLE IN JOBS PAGE
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_data(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the JobFilter with request GET data
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(published=1).all().order_by('-created_at'))
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

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

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

# ---------------------------fetch job details section-------------------------


@login_required(login_url='login')
def fetch_job_details(request):
    if request.method == 'GET':
        product_id = request.GET.get('id')
        try:
            job = Job.objects.get(id=product_id)
            firstname = job.first_name
            lastname = job.last_name
            customerName = f"{firstname or 'N/A'} {lastname or 'N/A'}"
            agent = job.agent

            addedByfirstname = ""
            addedBylastname = ""
            addedByfullname = ""
            if job.created_by:
                addedByfirstname = job.created_by.first_name
                addedBylastname = job.created_by.last_name
                addedByfullname = addedByfirstname + " " + addedBylastname

            assignedByfirstname = ""
            assignedBylastname = ""
            assignedByfullname = ""
            if job.assignedBy:
                assignedByfirstname = job.assignedBy.first_name
                assignedBylastname = job.assignedBy.last_name
                assignedByfullname = assignedByfirstname + " " + assignedBylastname

            if agent is not None and hasattr(agent, 'fullname'):
                agent_fullname = agent.fullname
            else:
                agent_fullname = ''

            # Dictionary to map status values to badge HTML
            status_badge_mapping = {
                '0': '<span class="badge badge-warning">Undone</span>',
                '1': '<span class="badge badge-primary">Done</span>',
                '2': '<span class="badge badge-danger">Rejected</span>',
                # Provide a default badge if status doesn't match any of the above
                'default': '<span class="badge badge-warning">Undone</span>',
            }

            status = str(job.status)  # Convert status to a string
            # Get the badge HTML using the mapping dictionary or default badge
            status_badge = status_badge_mapping.get(
                status, status_badge_mapping['default'])

            data = {
                'id': job.pk,
                'client': job.client.client_name,
                'agent': agent_fullname,
                'ref': job.ref_no,
                'clientrefNo': job.clientJobrefID,
                'name': customerName,
                'address': job.address,
                'email': job.email,
                'phone_number': job.phone_number,
                'state': job.state,
                'city': job.city,
                'batchno': job.BATCH_NO,
                'dateAdded': job.created_at.strftime('%Y-%m-%d %H:%M:%S %p'),
                'addedBy': addedByfullname,
                'assignedBy': assignedByfullname,
                'status': status_badge,  # Use the badge HTML
            }
            return JsonResponse(data)
        except Job.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ------------------View for rendering the edit job form---------------------
def edit_job_details(request):
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


# ====================View for updating job details=============================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def update_job(request):
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


# ------------------------Delete single and bulk jobs--------------------------
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def delete_job(request):
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


# =========================assign single/bulk assign section---------------
class AssignBulkJobView(View):
    def post(self, request, *args, **kwargs):
        if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            form = AssignForm(request.POST)
            if form.is_valid():
                agent = form.cleaned_data['agent']

                # Get current time
                current_datetime = timezone.localtime()
                print(current_datetime)
                job_ids = request.POST.getlist('job_ids[]')
                for id in job_ids:
                    if id.isnumeric():
                        jobs_updated = Job.objects.filter(pk=id).update(
                            agent=agent, status=0, whenAssigned=current_datetime, assignedBy=request.user)
                return JsonResponse({'success': True, 'message': f'{jobs_updated} jobs updated.'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid form data.'})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid request.'})
# =========================end of assign single/bulk assign section---------------

# =========================================END OF VIEW ALL JOBS SECTION===============================


# ---------------------------rejected jobs------------------------------
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def rejectedjobs(request):
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    # query all  rejectedjobs
    Total_rejectedjobs = Job.objects.all().filter(
        status=2).count()
    context = {
        'Total_rejectedjobs': Total_rejectedjobs,
        'profile': profile,
        "form": AssignForm(),  # this is for bulkassign so that the form will appear on modal
    }
    return render(request, 'staffs/jobs/rejectedjobs.html', context)


# ----------------------FETCH REJECTED JOB DATA INTO THE DATATABLE IN JOBS PAGE
# ---------------------------rejected jobs------------------------------
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def rejectedjobs(request):
    # To show loggedin Userprofile - who is adding job
    profile = get_object_or_404(UserProfile, user=request.user)

    # Create an instance of the JobFilter
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(status=2, published=1).order_by('-created_at'))

    Total_rejectedjobs = job_filter.qs.count()

    context = {
        'Total_rejectedjobs': Total_rejectedjobs,
        'profile': profile,
        'my_Filter': job_filter,  # Use the correct variable name
        "form": AssignForm(),  # this is for bulk assign so that the form will appear on modal
    }
    return render(request, 'staffs/jobs/rejectedjobs.html', context)


# ----------------------FETCH REJECTED JOB DATA INTO THE DATATABLE IN JOBS PAGE==================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetchrejected_job(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the JobFilter with request GET data
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(status=2, published=1))
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

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

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

# ==================================AGENT PENDING JOBS VIEW SECTION==========================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def agentpendingjobs(request):
    # To show logged-in UserProfile - who is adding the job
    profile = get_object_or_404(UserProfile, user=request.user)
    context = {
        'profile': profile,
    }
    return render(request, 'staffs/jobs/agentpendingjobs.html', context)


# ----------------------FETCH JOB DATA INTO THE DATATABLE IN JOBS PAGE
def fetch_allagentspendingjobs(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Define the columns to search in
    columns = ['agent__fullname', 'agent__user__last_login',
               'agent__user__phone_number']

    # Initialize the filter criteria
    filter_criteria = Q()

    if search_value:
        # Create an OR filter for each column to perform a case-insensitive search
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        filter_criteria &= search_filter

    # Filter pending jobs and group them by the agent who completed them
    agent_pending_jobs = Job.objects.filter(
        status=0, published=1).exclude(agent=None)

    data = agent_pending_jobs.values(
        'agent', 'agent__fullname', 'agent__created_at', 'agent__address', 'agent__user__is_active',
        'agent__guarantorName', 'agent__guarantorPhoneNumber', 'agent__BankAccountDetails',
        'agent__user__phone_number', 'agent__user__last_login'
    ).annotate(
        pending_job_count=Count('id')
    ).order_by('agent__fullname')

    # Apply the search filter to the data
    data = data.filter(filter_criteria)

    records_total = agent_pending_jobs.count()
    records_filtered = data.count()

    paginator = Paginator(data, length)
    page_number = (start // length) + 1
    data_page = paginator.page(page_number)

    def format_last_login(last_login):
        if last_login:
            return last_login.strftime('%b %d, %Y %I%p')
        return 'N/A'

    data = [
        {
            'agent_id': item['agent'],
            'agent__fullname': item['agent__fullname'],
            'pending_job_count': item['pending_job_count'],
            'agent__user__last_login': format_last_login(item['agent__user__last_login']),
            'agent__user__phone_number': item['agent__user__phone_number'],
            'agent__address': item['agent__address'],
            'agent__user__is_active': ' '.join([
                '<span class="badge badge-success">Active</span>' if item['agent__user__is_active']
                else '<span class="badge badge-danger">Inactive</span>'
            ]),
            'created_at': timezone.localtime(item['agent__created_at']).strftime('%Y-%m-%d %I:%M:%S %p') if item['agent__created_at'] else 'N/A',
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
# ==================================END OF AGENT PENDING JOBS VIEW SECTION==========================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def agentDetails(request):
    # To show logged-in UserProfile - who is adding the job
    profile = get_object_or_404(UserProfile, user=request.user)
    TotalAgents = Agent.objects.all().count()

    context = {
        'TotalAgents': TotalAgents,
        'profile': profile,
    }
    return render(request, 'agents/AgentDetails.html', context)


# ===============================fetch_agent_details==========================

def fetch_agent_details(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Define the columns to search in
    columns = ['fullname', 'address', 'guarantorPhoneNumber', 'guarantorName',
               'BankAccountDetails', 'user__userprofile__state', 'user__userprofile__city', 'user__email']

    # Initialize the filter criteria
    filter_criteria = Q()

    if search_value:
        # Create an OR filter for each column to perform a case-insensitive search
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        filter_criteria &= search_filter

    # Retrieve all agents
    agents = Agent.objects.all()

    # Apply the search filter to the agents
    agents = agents.filter(filter_criteria)

    records_total = agents.count()
    records_filtered = records_total

    paginator = Paginator(agents, length)
    page_number = (start // length) + 1
    agents_page = paginator.page(page_number)

    # Format the agents data for DataTables
    data = [
        {
            'id': agent.id,
            'profile_picture': '<img src="' + agent.user.userprofile.profile_picture.url + '" style="max-width: 100px; max-height: 100px;">' if agent.user.userprofile.profile_picture else 'N/A',
            'fullname': agent.fullname,
            'email': agent.user.email,
            'PhoneNumber': agent.user.phone_number,
            'address': agent.address,
            'state': agent.user.userprofile.state or 'None',
            'city': agent.user.userprofile.city or 'None',
            'is_active': '<span class="badge badge-success">Active</span>' if agent.is_active else '<span class="badge badge-danger">Inactive</span>',
            'last_login': timesince(agent.user.last_login) if agent.user.last_login else 'N/A',
            'proofOfId': '<a href="' + agent.proofOfId.url + '" download>Download</a>' if agent.proofOfId else 'N/A',
            'guarantorPhoneNumber': agent.guarantorPhoneNumber,
            'guarantorName': agent.guarantorName,
            'BankAccountDetails': agent.BankAccountDetails,
            'created_at': timezone.localtime(agent.created_at).strftime('%Y-%m-%d %I:%M:%S %p') if agent.created_at else 'N/A',
        }
        for agent in agents_page
    ]

    response = {
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
    }

    return JsonResponse(response)

# ===========fetch fetch agents on Modal


def fetchagentDetailsModal(request):
    if request.method == 'GET':
        agent_id = request.GET.get('id')
        try:
            agent = Agent.objects.get(id=agent_id)

            # In your view, convert the profile picture and proof of ID fields to their URLs
            profile_picture_url = agent.user.userprofile.profile_picture.url if agent.user.userprofile.profile_picture else ''
            proof_of_id_url = agent.proofOfId.url if agent.proofOfId else ''

            data = {
                'id': agent.id,
                'fullname': agent.fullname,
                'AgentEmail': agent.user.email,
                'PhoneNumber': agent.user.phone_number,
                'Agentaddress': agent.address,
                'Agentstate': agent.user.userprofile.state or 'None',
                'Agentcity': agent.user.userprofile.city or 'None',
                'is_active': '<span class="badge badge-success">Active</span>' if agent.is_active else '<span class="badge badge-danger">Inactive</span>',
                'last_login': timesince(agent.user.last_login) if agent.user.last_login else 'N/A',
                'guarantorPhoneNumber': agent.guarantorPhoneNumber,
                'guarantorName': agent.guarantorName,
                'BankAccountDetails': agent.BankAccountDetails,
                'created_at': agent.created_at.strftime('%Y-%m-%d %H:%M:%S %p'),
                'profile_picture': profile_picture_url,
                'proofOfId': proof_of_id_url,
            }
            return JsonResponse(data)
        except Agent.DoesNotExist:
            return JsonResponse({'error': 'Agent not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def agent_jobs(request, agent_id):
    # Your existing code to fetch agent and jobs
    agent = Agent.objects.get(id=agent_id)
    agent_jobs = Job.objects.filter(agent=agent, status=0, published=1)

    # Serialize the queryset to JSON
    jobs_json = serializers.serialize('json', agent_jobs)

    # Return JSON response to the AJAX request
    return JsonResponse({'data': jobs_json})


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetchlistsofagentjob(request, agent_id):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    columns = ['ref_no', 'clientJobrefID', 'first_name', 'last_name', 'address',
               'state', 'city', 'client__client_name', 'created_at', 'agent__fullname']

    # Initialize the filter criteria
    filter_criteria = Q(status=0, published=1, agent_id=agent_id)

    if search_value:
        # Add the search filter conditions to the existing filter criteria
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        if ' ' in search_value:
            first_name, last_name = search_value.split(' ', 1)
            search_filter |= (Q(first_name__icontains=first_name)
                              & Q(last_name__icontains=last_name))
        filter_criteria &= search_filter

    data = Job.objects.filter(filter_criteria).order_by(
        '-created_at')  # Sort by the original created_at field

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

# =============================================ALL UNASSIGNED JOBS==================================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def unassignedjobs(request):
    # To show loggedin Userprofile - who is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    # query all unassigned jobs but only those published by clients
    # get all unassigned Jobs
    Total_unassigned_jobs = Job.objects.filter(
        agent=None, status=0, published=1).all().count()

    # Create an instance of the JobFilter for unassigned jobs
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(agent=None, status=0, published=1).all())

    context = {
        'Total_unassigned_jobs': Total_unassigned_jobs,
        'profile': profile,
        'my_Filter': job_filter,  # Use the correct variable name
        'form': AssignForm(),  # this is for bulkassign so that the form will appear on modal
    }
    return render(request, 'staffs/jobs/unassignedjobs.html', context)

# ----------------------FETCH JOB DATA INTO THE DATATABLE IN JOBS PAGE


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_unassigneddata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the JobFilter with request GET data for unassigned jobs
    job_filter = JobFilter(
        request.GET, queryset=Job.objects.filter(agent=None, status=0, published=1).all().order_by('-created_at'))
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

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

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
# ---------------------------fetch job details section-------------------------


# Adding job (CRUD for Jobs)  --best way of CRUD -using htmx
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def addjob(request):
    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            state = form.cleaned_data['state']
            city = form.cleaned_data['city']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            address = form.cleaned_data['address']
            client = form.cleaned_data['client']
            BATCH_NO = form.cleaned_data['BATCH_NO']
            job = form.save(commit=False)  # prepare to store

            # who created the job
            job.created_by = request.user
            job.status = 0  # set job to be pending

            # If clientJobrefID is empty, update it with ref_no== for clients like providus
            if not job.clientJobrefID:
                job.clientJobrefID = job.ref_no

            job.save()

            response = JsonResponse({
                'HX-Trigger': json.dumps({
                    "jobListChanged": None,
                    'HX-Trigger': 'modal#close',
                    "showMessage": "Job was added Successfully!",
                }),
                'HX-Redirect': reverse("unassignedjobs")
            }, status=204)

            return response
    else:
        form = JobForm()
    context = {
        'form': form,
    }
    return render(request, 'staffs/jobs/addnewjobform.html', context)


#################################### upload bulk job ######################################
class ImportView(View):
    def get(self, request, *args, **kwargs):
        # Prevent access to the page if not a staff
        if request.user.is_authenticated and request.user.role == User.STAFF:
            context = {"form": ImportForm()}
            return render(request, 'staffs/jobs/jobupload.html', context)
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

            return render(request, 'staffs/jobs/jobupload.html', context)

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

            return render(request, 'staffs/jobs/jobupload.html', context)
        
        
# ------------------END OF UNASSIGNED JOB SECTION----------------


# ---------------------ALL REPORTS DASHBOARD----------------------
# ------------------BULK REPORT UPLOAD SECTION----------------
# staff uploading bulk reports
class UploadReportViewbystaff(View):
    def get(self, request, *args, **kwargs):
        # Prevent access to the page if the user is not a staff
        if request.user.is_authenticated and request.user.role == User.STAFF:
            context = {
                "form": ImportReportForm(),
            }
            return render(request, 'staffs/reports/reportupload.html', context)
        else:
            return redirect('login')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        report_file = request.FILES.get("report_file")
        if not report_file:
            return HttpResponse("No file selected")

        rows = TextIOWrapper(
            report_file, encoding='unicode_escape', newline="")
        row_count = 0
        new_reports_count = 0
        updated_reports_count = 0
        skipped_reports_count = 0
        jobs_not_found_count = 0  # Initialize count for jobs not found
        form_errors = []

        verification_message_choices = dict(Report.VerificationMessage_choices)
        building_type_choices = dict(Report.buildingType_choices)
        building_condition_choices = dict(Report.buildingCondition_choices)
        customer_relationship_with_address_choices = dict(
            Report.CustomerRelationshipWithaddress_choices)
        address_residential_choices = dict(Report.AddressResidential_choices)

        for row in DictReader(rows):
            row_count += 1
            job_ref_no = row.get('JobRefNo')

            # Check for required fields in each row
            required_fields = [
                'VerificationMessage', 'buildingCondition', 'buildingColor',
                'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                'NameofindividualInterviewed', 'RelationshipWithCustomer', 'MoreComment', 'Landmark'
            ]
            missing_fields = [
                field for field in required_fields if not row.get(field)]
            if missing_fields:
                form_errors.append({
                    "row": row_count,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                })
                continue  # Skip processing this row if any required field is missing

            # Validate choice fields
            if row.get('VerificationMessage') not in verification_message_choices:
                form_errors.append({
                    "row": row_count,
                    "error": f"Invalid VerificationMessage: {row.get('VerificationMessage')}. "
                             f"Valid choices are: {', '.join(verification_message_choices.keys())}"
                })
                continue

            if row.get('buildingType') not in building_type_choices:
                form_errors.append({
                    "row": row_count,
                    "error": f"Invalid buildingType: {row.get('buildingType')}. "
                             f"Valid choices are: {', '.join(building_type_choices.keys())}"
                })
                continue

            if row.get('buildingCondition') not in building_condition_choices:
                form_errors.append({
                    "row": row_count,
                    "error": f"Invalid buildingCondition: {row.get('buildingCondition')}. "
                             f"Valid choices are: {', '.join(building_condition_choices.keys())}"
                })
                continue

            if row.get('CustomerRelationshipWithaddress') not in customer_relationship_with_address_choices:
                form_errors.append({
                    "row": row_count,
                    "error": f"Invalid CustomerRelationshipWithaddress: {row.get('CustomerRelationshipWithaddress')}. "
                             f"Valid choices are: {', '.join(customer_relationship_with_address_choices.keys())}"
                })
                continue

            if row.get('AddressResidential') not in address_residential_choices:
                form_errors.append({
                    "row": row_count,
                    "error": f"Invalid AddressResidential: {row.get('AddressResidential')}. "
                             f"Valid choices are: {', '.join(address_residential_choices.keys())}"
                })
                continue

            try:
                # Fetch corresponding Job object
                job = Job.objects.get(ref_no=job_ref_no)
                whenAssigned = job.whenAssigned

                # Calculate TAT and update other fields
                current_datetime = timezone.now()
                date_format1 = parser.parse(str(current_datetime))

                whenJobAssigned_str = whenAssigned.strftime(
                    "%b. %d, %Y, %I:%M %p")
                if 'midnight' in whenJobAssigned_str:
                    whenJobAssigned_str = whenJobAssigned_str.replace(
                        'midnight', '12:00am')
                elif 'noon' in whenJobAssigned_str:
                    whenJobAssigned_str = whenJobAssigned_str.replace(
                        'noon', '12:00pm')

                date_format2 = parser.parse(whenJobAssigned_str)
                date_format2 = timezone.make_aware(date_format2)
                diff = date_format1 - date_format2
                total_TAT = diff.total_seconds() / 3600  # Calculate TAT in hours

                # Update existing report or create a new one
                existing_report = Report.objects.filter(customer=job).first()
                if existing_report:
                    # Check if any fields are different, if not, skip updating
                    fields_to_check = [
                        'TAT', 'JobRefNo', 'address', 'clientJobrefID', 'Client',
                        'agent', 'VerificationMessage', 'buildingCondition', 'buildingColor',
                        'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                        'NameofindividualInterviewed', 'RelationshipWithCustomer', 'MoreComment',
                        'Landmark', 'modified_at', 'customerName'
                    ]
                    fields_changed = any(
                        getattr(existing_report, field) != row.get(field) for field in fields_to_check
                    )
                    if fields_changed:
                        existing_report.TAT = total_TAT
                        existing_report.JobRefNo = str(job_ref_no)
                        existing_report.address = str(job.address)
                        existing_report.clientJobrefID = str(
                            job.clientJobrefID)
                        existing_report.Client = str(job.client)
                        existing_report.agent = str(job.agent)
                        existing_report.VerificationMessage = row.get(
                            'VerificationMessage')
                        existing_report.buildingCondition = row.get(
                            'buildingCondition')
                        existing_report.buildingColor = row.get(
                            'buildingColor')
                        existing_report.buildingType = row.get('buildingType')
                        existing_report.CustomerRelationshipWithaddress = row.get(
                            'CustomerRelationshipWithaddress')
                        existing_report.AddressResidential = row.get(
                            'AddressResidential')
                        existing_report.NameofindividualInterviewed = row.get(
                            'NameofindividualInterviewed')
                        existing_report.RelationshipWithCustomer = row.get(
                            'RelationshipWithCustomer')
                        existing_report.MoreComment = row.get('MoreComment')
                        existing_report.Landmark = row.get('Landmark')
                        existing_report.modified_at = date_format1
                        existing_report.created_at = existing_report.created_at
                        existing_report.customerName = f"{job.first_name} {job.last_name}"
                        existing_report.save()
                        updated_reports_count += 1
                    else:
                        skipped_reports_count += 1
                        continue  # No changes, skip updating
                else:
                    new_report = Report.objects.create(
                        customer=job,
                        TAT=total_TAT,
                        JobRefNo=str(job_ref_no),
                        address=str(job.address),
                        clientJobrefID=str(job.clientJobrefID),
                        Client=str(job.client),
                        agent=str(job.agent),
                        VerificationMessage=row.get('VerificationMessage'),
                        buildingCondition=row.get('buildingCondition'),
                        buildingColor=row.get('buildingColor'),
                        buildingType=row.get('buildingType'),
                        CustomerRelationshipWithaddress=row.get(
                            'CustomerRelationshipWithaddress'),
                        AddressResidential=row.get('AddressResidential'),
                        NameofindividualInterviewed=row.get(
                            'NameofindividualInterviewed'),
                        RelationshipWithCustomer=row.get(
                            'RelationshipWithCustomer'),
                        MoreComment=row.get('MoreComment'),
                        Landmark=row.get('Landmark'),
                        modified_at=date_format1,
                        created_at=date_format1,
                        customerName=f"{job.first_name} {job.last_name}",
                    )
                    new_reports_count += 1

                # update the status field in Jobs table when reports are uploaded
                Job.objects.filter(ref_no=job_ref_no).update(status=1)

            except Job.DoesNotExist:
                jobs_not_found_count += 1  # Increment count for jobs not found
                continue  # Move to the next row if Job object does not exist
            except Job.MultipleObjectsReturned:
                skipped_reports_count += 1
                continue  # Move to the next row if multiple Job objects are returned
            except IntegrityError:
                form_errors.append({
                    "row": row_count,
                    "error": "IntegrityError: Could not save the report due to database constraints."
                })
                continue  # Skip to the next row on integrity error

        context = {
            "form": ImportReportForm(),
            "form_errors": form_errors,
            "row_count": row_count,
            "new_reports_count": new_reports_count,
            "updated_reports_count": updated_reports_count,
            "skipped_reports_count": skipped_reports_count,
            "jobs_not_found_count": jobs_not_found_count,
        }
        return render(request, 'staffs/reports/reportupload.html', context)
# ------------------all reports-------------------------


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def allreports(request):
    # To show logged-in Userprofile - who is adding the job
    profile = get_object_or_404(UserProfile, user=request.user)

    # Create an instance of the ReportFilter
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.order_by('-created_at'))

    total_no_of_reports = report_filter.qs.count()

    context = {
        'profile': profile,
        'total_no_of_reports': total_no_of_reports,
        'my_Filter': report_filter,
    }
    return render(request, 'staffs/reports/allreports.html', context)

# ------------------fetch all reportdata-------------------------


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_allreportdata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the ReportFilter with request GET data
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.order_by('-created_at'))
    data = report_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus', 'buildingCondition', 'buildingColor', 'buildingType',
                   'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        data = data.filter(search_filter)

     # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

    records_total = Report.objects.count()
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
            'buildingCondition': item.buildingCondition,
            'buildingColor': item.buildingColor,
            'buildingType': item.buildingType,
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


# ============================ Edit all Report==========================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def EditallReport(request, pk=None):
    selected_report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        Reportform = EditReportForm(
            request.POST, request.FILES, instance=selected_report)

        if Reportform.is_valid():
            buildingCondition = Reportform.cleaned_data['buildingCondition']
            buildingColor = Reportform.cleaned_data['buildingColor']
            buildingType = Reportform.cleaned_data['buildingType']
            CustomerRelationshipWithaddress = Reportform.cleaned_data[
                'CustomerRelationshipWithaddress']
            AddressResidential = Reportform.cleaned_data['AddressResidential']
            NameofindividualInterviewed = Reportform.cleaned_data['NameofindividualInterviewed']
            RelationshipWithCustomer = Reportform.cleaned_data['RelationshipWithCustomer']
            VerificationMessage = Reportform.cleaned_data['VerificationMessage']
            MoreComment = Reportform.cleaned_data['MoreComment']
            Landmark = Reportform.cleaned_data['Landmark']
            photo1 = Reportform.cleaned_data['photo1']
            photo2 = Reportform.cleaned_data['photo2']

            reportjob = Reportform.save(commit=False)  # prepare to store
            reportjob.save()
            return redirect('allreports')

        else:
            print('invalid form')
            print(Reportform.errors)

    else:
        Reportform = EditReportForm(instance=selected_report)

    context = {
        'selected_report': selected_report,
        'Reportform': Reportform,
    }
    return render(request, 'staffs/reports/EditallReportForm.html', context)


class allreportbulk_approvalView(View):
    def post(self, request, *args, **kwargs):
        if request.method == "POST":
            # Get the selected report IDs
            report_ids = request.POST.getlist('ids[]')
            # Get the current datetime in your local timezone
            current_datetime = timezone.now()
            # Format the datetime as a string with the desired format
            date_format1 = current_datetime.strftime("%Y-%m-%d %H:%M:%S.%f%z")

            for report_id in report_ids:
                # Retrieve the report based on the ID
                selected_report = Report.objects.filter(pk=report_id).first()
                if selected_report and selected_report.Client == "Wema":
                    try:
                        # Approve the report
                        selected_report.Reportstatus = 1
                        selected_report.modified_at = date_format1
                        selected_report.approvedBy = request.user
                        selected_report.save()

                        # Extract details from selected_report
                        activity_id = selected_report.clientJobrefID
                        customer_name = f"{selected_report.customer.first_name} {selected_report.customer.last_name}"
                        address = selected_report.address
                        DateAdded = selected_report.created_at

                        parsed_datetime = DateAdded.astimezone(
                            timezone.get_current_timezone())
                        VisitDate = parsed_datetime.strftime("%b. %d, %Y")
                        VisitTime = parsed_datetime.strftime("%I:%M %p")

                        comment = selected_report.MoreComment
                        current_datetime = current_datetime.astimezone(
                            timezone.get_current_timezone())
                        ReceivedDate = DateAdded.strftime("%b. %d, %Y")
                        ReceivedTime = DateAdded.strftime("%I:%M %p")
                        PersonMetOthers = selected_report.RelationshipWithCustomer

                        photo_url = selected_report.photo1.url if selected_report.photo1 else "N/A"

                        address_exist_mapping = {
                            'Address exists and customer is known': True,
                        }

                        AddressExist = address_exist_mapping.get(
                            selected_report.VerificationMessage, False)

                        address_residential_mapping = {
                            'Yes': True,
                            'No': False,
                            'N/A': False,
                        }

                        AddressResidential = address_residential_mapping.get(
                            selected_report.AddressResidential, False)

                        VisitFeedback = "Passed" if AddressExist else "Failed"

                        payload = {
                            "ActivityId": activity_id,
                            "CustomerName": customer_name,
                            "VerificationAddress": address,
                            "VisitDate": VisitDate,
                            "VendorId": "6ce5c941-63c6-4da0-9639-dc7554d0a024",
                            "AddressExist": AddressExist,
                            "AddressResidential": AddressResidential,
                            "CustomerResident": AddressResidential,
                            "CustomerKnown": AddressExist,
                            "MetWith": "N/A",
                            "EaseOfLocation": "No",
                            "Comments": comment,
                            "ReceivedDate": ReceivedDate,
                            "VisitTime": VisitTime,
                            "PersonMetOthers": PersonMetOthers,
                            "NameOfPersonMet": PersonMetOthers,
                            "VisitFeedback": VisitFeedback,
                            "AddressImage": [
                                {
                                    "CustomerId": "N/A",
                                    "FileName": "N/A",
                                    "FileType": "N/A",
                                    "ImageUrl": photo_url
                                }
                            ]
                        }

                        api_url = 'https://apibox.alat.ng/digitaloperationsonboarding/api/addressVerification/AddressVerificationResponse'
                        headers = {'Content-Type': 'application/json'}
                        response = requests.post(
                            api_url, data=json.dumps(payload), headers=headers)

                        if response.status_code == 200:
                            api_response = response.json()
                            print("Success Message:", api_response.get(
                                "message", "API response message not found"))
                        else:
                            print(
                                "Failed to send report to API. Status code:", response.status_code)
                            # Rollback approval if API call fails
                            selected_report.Reportstatus = 0
                            selected_report.save()

                    except Exception as e:
                        print("Exception occurred while processing report:", str(e))

                elif selected_report:
                    # Approve the report without sending to the API for UBA and Providus
                    selected_report.Reportstatus = 1
                    selected_report.modified_at = date_format1
                    selected_report.approvedBy = request.user
                    selected_report.save()

                else:
                    print(
                        "Report not sent. Reportstatus is not 1 or Client is not 'Wema'.")

            return JsonResponse({'message': 'Bulk approval completed'})

        return redirect('allreports')

# ---------------------END OF ALL REPORTS DASHBOARD----------------------


# ----------------------PENDING DASHBOARD SECTION----------------
# Pending Reports
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def Pendingreports(request):
    # To show loggedin Userprofile - who is adding the job
    profile = get_object_or_404(UserProfile, user=request.user)

    # Create an instance of the ReportFilter
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=0).order_by('created_at'))

    totalpending_no_of_reports = report_filter.qs.count()

    context = {
        'profile': profile,
        'totalpending_no_of_reports': totalpending_no_of_reports,
        'my_Filter': report_filter,  # Use the correct variable name
    }
    return render(request, 'staffs/reports/pendingreports.html', context)

# ----------------------FETCH REPORT DATA INTO THE DATATABLE IN REPORTS PAGE


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_pendingreportdata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the ReportFilter with request GET data
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=0).order_by('-created_at'))
    data = report_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus',
                   'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        data = data.filter(search_filter)

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

    records_total = Report.objects.count()
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
            'customerName': f"{item.customer.first_name or 'N/A'} {item.customer.last_name or 'N/A'}",
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

@login_required(login_url='login')
def fetch_report_details(request):
    if request.method == 'GET':
        product_id = request.GET.get('id')
        try:
            # Fetch the report from the database
            job = Report.objects.get(id=product_id)
            firstname = job.customer.first_name
            lastname = job.customer.last_name
            customerName = f"{firstname or 'N/A'} {lastname or 'N/A'}"

            # Prepare Approved By Full Name
            approvedByfirstname = ""
            approvedBylastname = ""
            approvedByfullname = ""
            if job.approvedBy:
                approvedByfirstname = job.approvedBy.first_name
                approvedBylastname = job.approvedBy.last_name
                approvedByfullname = approvedByfirstname + " " + approvedBylastname

            # Verification Status Mapping
            verification_status = 'N/A'
            verification_mapping = {
                'Incomplete Information': 'No - No',
                'No Response at the Address': 'Yes - No',
                'Address Does Not Exist': 'No - No',
                'Security Agents prevented access to Address': 'Yes - No',
                'Address is an empty plot of Land': 'Yes - No',
                'The Customer has relocated': 'Yes - No',
                'The Customer is not known at the address': 'Yes - No',
                'The Customer is known but does not reside in the premises': 'Yes - No',
                'Address exists and customer is known': 'Yes - Yes',
                'Customer does not live at the address but visits often': 'Yes - No',
                'The Customer is deceased': 'Yes - No',
                'Could not locate address': 'No - No',
                'The Customer works at the address but does not reside there': 'Yes - No',
                'Customer was met at a different house number': 'No - No',
                'Address is customers family house and does not reside there': 'Yes - No',
                'Company is not known at the address': 'Yes - No',
                'Incomplete address': 'No - No',
                'Company is known and operate from the address': 'Yes - Yes'
            }
            verification_status = verification_mapping.get(job.VerificationMessage, 'N/A')

            # Color-coded Reportstatus
            report_status = 'N/A'
            if job.Reportstatus == '0':
                report_status = '<span class="badge badge-warning">Pending</span>'
            elif job.Reportstatus == '1':
                report_status = '<span class="badge badge-primary">Approved</span>'
            elif job.Reportstatus == '2':
                report_status = '<span class="badge badge-danger">Rejected</span>'
            else:
                report_status = '<span class="badge badge-warning">Pending</span>'

            # Image URLs
            photo1_url = job.photo1.url if job.photo1 else ''
            photo2_url = job.photo2.url if job.photo2 else ''

            # Get the URL for downloading the report PDF
            download_link = reverse('reportinPdf', kwargs={'pk': job.pk})

            # Get latitude and longitude from the model
            latitude = job.latitude
            longitude = job.longitude

            # Prepare the data to send as JSON response
            data = {
                'downloadLink': download_link,  # Include the download link
                'id': job.pk,
                'client': job.Client,
                'agent': job.agent,
                'clientrefNo': job.clientJobrefID,
                'name': customerName,
                'customeraddress': job.address,
                'latitude': latitude,
                'longitude': longitude,
                'TAT': job.TAT,
                'VerificationMessage': job.VerificationMessage,
                'VerificationStatus': verification_status,
                'BuildingCondition': job.buildingCondition,
                'buildingColor': job.buildingColor,
                'buildingType': job.buildingType,
                'CustomerRelationshipWithaddress': job.CustomerRelationshipWithaddress,
                'AddressResidential': job.AddressResidential,
                'NameofindividualInterviewed': job.NameofindividualInterviewed,
                'RelationshipWithCustomer': job.RelationshipWithCustomer,
                'MoreComment': job.MoreComment,
                'Landmark': job.Landmark,
                'photo1': photo1_url,  # Use the URL of the image
                'photo2': photo2_url,  # Use the URL of the image
                'approvedBy': approvedByfullname,
                'Reportstatus': report_status,  # Use the badge HTML
                'dateAdded': job.created_at.strftime('%Y-%m-%d %H:%M:%S %p'),
            }
            return JsonResponse(data)
        except Report.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=404)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ------------------View for rendering the report job form---------------------
# ===========================Edit Pending Report=========================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def EditPendingReport(request, pk=None):
    selected_report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        Reportform = EditReportForm(
            request.POST, request.FILES, instance=selected_report)

        if Reportform.is_valid():
            buildingCondition = Reportform.cleaned_data['buildingCondition']
            buildingColor = Reportform.cleaned_data['buildingColor']
            buildingType = Reportform.cleaned_data['buildingType']
            CustomerRelationshipWithaddress = Reportform.cleaned_data[
                'CustomerRelationshipWithaddress']
            AddressResidential = Reportform.cleaned_data['AddressResidential']
            NameofindividualInterviewed = Reportform.cleaned_data['NameofindividualInterviewed']
            RelationshipWithCustomer = Reportform.cleaned_data['RelationshipWithCustomer']
            VerificationMessage = Reportform.cleaned_data['VerificationMessage']
            MoreComment = Reportform.cleaned_data['MoreComment']
            Landmark = Reportform.cleaned_data['Landmark']
            photo1 = Reportform.cleaned_data['photo1']
            photo2 = Reportform.cleaned_data['photo2']

            reportjob = Reportform.save(commit=False)  # prepare to store
            reportjob.save()
            return redirect('pendingreports')

        else:
            print('invalid form')
            print(Reportform.errors)

    else:
        Reportform = EditReportForm(instance=selected_report)

    context = {
        'selected_report': selected_report,
        'Reportform': Reportform,
    }
    return render(request, 'staffs/reports/PendingEditreportform.html', context)
# ===========================End of Edit Pending Report=========================


# ========================== Bulk Report Approval=============================
class PendingBulkReportApprovalView(View):
    def post(self, request, *args, **kwargs):
        if request.method == "POST":
            # Get the selected report IDs
            report_ids = request.POST.getlist('ids[]')
            # Get the current datetime in your local timezone
            current_datetime = timezone.now()
            # Format the datetime as a string with the desired format
            date_format1 = current_datetime.strftime("%Y-%m-%d %H:%M:%S.%f%z")

            for report_id in report_ids:
                # Retrieve the report based on the ID
                selected_report = Report.objects.filter(pk=report_id).first()
                if selected_report and selected_report.Client == "Wema":
                    try:
                        # Approve the report
                        selected_report.Reportstatus = 1
                        selected_report.modified_at = date_format1
                        selected_report.approvedBy = request.user
                        selected_report.save()

                        # Extract details from selected_report
                        activity_id = selected_report.clientJobrefID
                        customer_name = f"{selected_report.customer.first_name} {selected_report.customer.last_name}"
                        address = selected_report.address
                        DateAdded = selected_report.created_at

                        parsed_datetime = DateAdded.astimezone(
                            timezone.get_current_timezone())
                        VisitDate = parsed_datetime.strftime("%b. %d, %Y")
                        VisitTime = parsed_datetime.strftime("%I:%M %p")

                        comment = selected_report.MoreComment
                        current_datetime = current_datetime.astimezone(
                            timezone.get_current_timezone())
                        ReceivedDate = DateAdded.strftime("%b. %d, %Y")
                        ReceivedTime = DateAdded.strftime("%I:%M %p")
                        PersonMetOthers = selected_report.RelationshipWithCustomer

                        photo_url = selected_report.photo1.url if selected_report.photo1 else "N/A"

                        address_exist_mapping = {
                            'Address exists and customer is known': True,
                        }

                        AddressExist = address_exist_mapping.get(
                            selected_report.VerificationMessage, False)

                        address_residential_mapping = {
                            'Yes': True,
                            'No': False,
                            'N/A': False,
                        }

                        AddressResidential = address_residential_mapping.get(
                            selected_report.AddressResidential, False)

                        VisitFeedback = "Passed" if AddressExist else "Failed"

                        payload = {
                            "ActivityId": activity_id,
                            "CustomerName": customer_name,
                            "VerificationAddress": address,
                            "VisitDate": VisitDate,
                            "VendorId": "6ce5c941-63c6-4da0-9639-dc7554d0a024",
                            "AddressExist": AddressExist,
                            "AddressResidential": AddressResidential,
                            "CustomerResident": AddressResidential,
                            "CustomerKnown": AddressExist,
                            "MetWith": "N/A",
                            "EaseOfLocation": "No",
                            "Comments": comment,
                            "ReceivedDate": ReceivedDate,
                            "VisitTime": VisitTime,
                            "PersonMetOthers": PersonMetOthers,
                            "NameOfPersonMet": PersonMetOthers,
                            "VisitFeedback": VisitFeedback,
                            "AddressImage": [
                                {
                                    "CustomerId": "N/A",
                                    "FileName": "N/A",
                                    "FileType": "N/A",
                                    "ImageUrl": photo_url
                                }
                            ]
                        }

                        api_url = 'https://apibox.alat.ng/digitaloperationsonboarding/api/addressVerification/AddressVerificationResponse'
                        headers = {'Content-Type': 'application/json'}
                        response = requests.post(
                            api_url, data=json.dumps(payload), headers=headers)

                        if response.status_code == 200:
                            api_response = response.json()
                            print("Success Message:", api_response.get(
                                "message", "API response message not found"))
                        else:
                            print(
                                "Failed to send report to API. Status code:", response.status_code)
                            print("API response content:",
                                  response.content.decode())
                            # Rollback approval if API call fails
                            selected_report.Reportstatus = 0
                            selected_report.save()

                    except Exception as e:
                        print("Exception occurred while processing report:", str(e))

                elif selected_report:
                    # Approve the report without sending to the API for UBA and Providus
                    selected_report.Reportstatus = 1
                    selected_report.modified_at = date_format1
                    selected_report.approvedBy = request.user
                    selected_report.save()

                else:
                    print(
                        "Report not sent. Reportstatus is not 1 or Client is not 'Wema'.")

            return JsonResponse({'message': 'Bulk approval completed'})

        return redirect('pendingreports')

# ==========================End Bulk Report Approval=============================


# ==============================================Rejected Reports=================================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def rejectedreports(request):
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    # get all reports
    totalrejected_no_of_reports = Report.objects.filter(
        Reportstatus=2).order_by('created_at').count()

    context = {
        'profile': profile,
        'totalrejected_no_of_reports': totalrejected_no_of_reports,
    }
    return render(request, 'staffs/reports/rejectedreports.html', context)


# ================FETCH REJECTED REPORTS==============
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def rejectedreports(request):
    # To show loggedin Userprofile - who is adding job
    profile = get_object_or_404(UserProfile, user=request.user)

    # Create an instance of the ReportFilter
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=2).order_by('created_at'))

    totalrejected_no_of_reports = report_filter.qs.count()

    context = {
        'profile': profile,
        'totalrejected_no_of_reports': totalrejected_no_of_reports,
        'my_Filter': report_filter,  # Use the correct variable name
    }
    return render(request, 'staffs/reports/rejectedreports.html', context)


# ================FETCH REJECTED REPORTS==============
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_rejectedreportdata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the ReportFilter with request GET data
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=2).order_by('-created_at'))
    data = report_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus',
                   'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        data = data.filter(search_filter)

     # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

    records_total = Report.objects.count()
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
            'customerName': f"{item.customer.first_name or 'N/A'} {item.customer.last_name or 'N/A'}",
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
# ===========================END OF REJECTED REPORTS------------------------------


# ===============================EditRejectedReport===================================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def EditRejectedReport(request, pk=None):
    selected_report = get_object_or_404(Report, pk=pk)

    if request.method == 'POST':
        Reportform = EditReportForm(
            request.POST, request.FILES, instance=selected_report)

        if Reportform.is_valid():
            buildingCondition = Reportform.cleaned_data['buildingCondition']
            buildingColor = Reportform.cleaned_data['buildingColor']
            buildingType = Reportform.cleaned_data['buildingType']
            CustomerRelationshipWithaddress = Reportform.cleaned_data[
                'CustomerRelationshipWithaddress']
            AddressResidential = Reportform.cleaned_data['AddressResidential']
            NameofindividualInterviewed = Reportform.cleaned_data['NameofindividualInterviewed']
            RelationshipWithCustomer = Reportform.cleaned_data['RelationshipWithCustomer']
            VerificationMessage = Reportform.cleaned_data['VerificationMessage']
            MoreComment = Reportform.cleaned_data['MoreComment']
            Landmark = Reportform.cleaned_data['Landmark']
            photo1 = Reportform.cleaned_data['photo1']
            photo2 = Reportform.cleaned_data['photo2']

            reportjob = Reportform.save(commit=False)  # prepare to store
            reportjob.save()
            return redirect('rejectedreports')

        else:
            print('invalid form')
            print(Reportform.errors)

    else:
        Reportform = EditReportForm(instance=selected_report)

    context = {
        'selected_report': selected_report,
        'Reportform': Reportform,
    }
    return render(request, 'staffs/reports/EditRejectedform.html', context)
# ==================================End of EditRejectedReport=============================


# ========================== Approve Rejected Bulk Report=============================
class RejectedBulkReportApprovalView(View):
    def post(self, request, *args, **kwargs):
        if request.method == "POST":
            # Get the selected report IDs
            report_ids = request.POST.getlist('ids[]')
            # Get the current datetime in your local timezone
            current_datetime = timezone.now()
            # Format the datetime as a string with the desired format
            date_format1 = current_datetime.strftime("%Y-%m-%d %H:%M:%S.%f%z")

            for report_id in report_ids:
                # Retrieve the report based on the ID
                selected_report = Report.objects.filter(pk=report_id).first()
                if selected_report and selected_report.Client == "Wema":
                    try:
                        # Approve the report
                        selected_report.Reportstatus = 1
                        selected_report.modified_at = date_format1
                        selected_report.approvedBy = request.user
                        selected_report.save()

                        # Extract details from selected_report
                        activity_id = selected_report.clientJobrefID
                        customer_name = f"{selected_report.customer.first_name} {selected_report.customer.last_name}"
                        address = selected_report.address
                        DateAdded = selected_report.created_at

                        parsed_datetime = DateAdded.astimezone(
                            timezone.get_current_timezone())
                        VisitDate = parsed_datetime.strftime("%b. %d, %Y")
                        VisitTime = parsed_datetime.strftime("%I:%M %p")

                        comment = selected_report.MoreComment
                        current_datetime = current_datetime.astimezone(
                            timezone.get_current_timezone())
                        ReceivedDate = DateAdded.strftime("%b. %d, %Y")
                        ReceivedTime = DateAdded.strftime("%I:%M %p")
                        PersonMetOthers = selected_report.RelationshipWithCustomer

                        photo_url = selected_report.photo1.url if selected_report.photo1 else "N/A"

                        address_exist_mapping = {
                            'Address exists and customer is known': True,
                        }

                        AddressExist = address_exist_mapping.get(
                            selected_report.VerificationMessage, False)

                        address_residential_mapping = {
                            'Yes': True,
                            'No': False,
                            'N/A': False,
                        }

                        AddressResidential = address_residential_mapping.get(
                            selected_report.AddressResidential, False)

                        VisitFeedback = "Passed" if AddressExist else "Failed"

                        payload = {
                            "ActivityId": activity_id,
                            "CustomerName": customer_name,
                            "VerificationAddress": address,
                            "VisitDate": VisitDate,
                            "VendorId": "6ce5c941-63c6-4da0-9639-dc7554d0a024",
                            "AddressExist": AddressExist,
                            "AddressResidential": AddressResidential,
                            "CustomerResident": AddressResidential,
                            "CustomerKnown": AddressExist,
                            "MetWith": "N/A",
                            "EaseOfLocation": "No",
                            "Comments": comment,
                            "ReceivedDate": ReceivedDate,
                            "VisitTime": VisitTime,
                            "PersonMetOthers": PersonMetOthers,
                            "NameOfPersonMet": PersonMetOthers,
                            "VisitFeedback": VisitFeedback,
                            "AddressImage": [
                                {
                                    "CustomerId": "N/A",
                                    "FileName": "N/A",
                                    "FileType": "N/A",
                                    "ImageUrl": photo_url
                                }
                            ]
                        }

                        api_url = 'https://apibox.alat.ng/digitaloperationsonboarding/api/addressVerification/AddressVerificationResponse'
                        headers = {'Content-Type': 'application/json'}
                        response = requests.post(
                            api_url, data=json.dumps(payload), headers=headers)

                        if response.status_code == 200:
                            api_response = response.json()
                            print("Success Message:", api_response.get(
                                "message", "API response message not found"))
                        else:
                            print(
                                "Failed to send report to API. Status code:", response.status_code)
                            # Rollback approval if API call fails
                            selected_report.Reportstatus = 0
                            selected_report.save()

                    except Exception as e:
                        print("Exception occurred while processing report:", str(e))

                elif selected_report:
                    # Approve the report without sending to the API for UBA and Providus
                    selected_report.Reportstatus = 1
                    selected_report.modified_at = date_format1
                    selected_report.approvedBy = request.user
                    selected_report.save()

                else:
                    print(
                        "Report not sent. Reportstatus is not 1 or Client is not 'Wema'.")

            return JsonResponse({'message': 'Bulk approval completed'})

        return redirect('rejectedreports')
# ==========================End of Bulk Report Approval for rejected report=============================


# ===========================DELETE REPORTS==================================
def delete_report(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)

        # Update the connected job's status to '0'
        job = report.customer
        job.status = '0'  # Use '0' as a string
        job.agent = None  # Remove the agent from the job
        job.whenAssigned = None  # Remove whenAssigned if necessary

        # Save the job to persist the changes in the database
        job.save()

        # Now you can safely delete the report
        report.delete()

        return JsonResponse({'message': 'Report deleted successfully'})

    return JsonResponse({'message': 'Invalid request'}, status=400)


# ===========================APPROVED REPORTS==================================
# Approved Reports
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def Approvedreports(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    # Create an instance of the ApprovedReportFilter
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=1).order_by('created_at'))

    totalapproved_no_of_reports = report_filter.qs.count()

    context = {
        'profile': profile,
        'totalapproved_no_of_reports': totalapproved_no_of_reports,
        'my_Filter': report_filter,
    }
    return render(request, 'staffs/reports/ApprovedReports.html', context)

# ----------------------FETCH APPROVED REPORT DATA INTO THE DATATABLE IN APPROVED REPORTS PAGE


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def fetch_approvedreportdata(request):
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    # Initialize the ApprovedReportFilter with request GET data
    report_filter = ReportFilter(
        request.GET, queryset=Report.objects.filter(Reportstatus=1).order_by('-created_at'))
    data = report_filter.qs

    # If there's a DataTables search value, add it to the filter criteria
    if search_value:
        columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus',
                   'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        data = data.filter(search_filter)

    # Date range filtering
    start_date = request.GET.get('created_at_0')
    end_date = request.GET.get('created_at_1')
    if start_date and end_date:
        data = data.filter(created_at__range=(start_date, end_date))

    records_total = Report.objects.count()
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
            'customerName': f"{item.customer.first_name or 'N/A'} {item.customer.last_name or 'N/A'}",
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
# ===========================END APPROVED REPORTS==================================


# =================Generate a PDF File of a Report Detail================================
def reportinPdf(request, pk):
    response = HttpResponse(content_type='application/pdf')
    today = datetime.now()
    # Create Bytestream buffer
    buffer = BytesIO()
    # Create a canvas
    p = canvas.Canvas(buffer, pagesize=A4)

    my_Style = ParagraphStyle('My Para style',
                              fontName='Helvetica',
                              fontSize=10,
                              leading=20,  # line spacing
                              alignment=0
                              )

    width, height = A4

    # Designate The Model (data) to print
    selected_report = get_object_or_404(Report, pk=pk)

 # Corrected customer name for the filename
    first_name = selected_report.customer.first_name or "Unknown"
    last_name = selected_report.customer.last_name or "Unknown"
    filename_customer_name = f"{first_name} {last_name}".strip()

    # Sanitize the filename to remove problematic characters
    filename_customer_name = ''.join(
        char for char in filename_customer_name if char.isalnum() or char in " -._")
    response['Content-Disposition'] = f'inline; filename="{filename_customer_name} Address Verification Report.pdf"'

# check status
    status = 'Pending'
    if selected_report.Reportstatus == '0':
        status = 'Pending'
    elif selected_report.Reportstatus == '1':
        status = 'Approved'
    elif selected_report.Reportstatus == '2':
        status = 'Rejected'

    # start writing the PD here
    my_image = ImageReader(
        'https://avr.percivaloaiya.com/static/assets/img/logo.jpg')
    p.setFont("Helvetica", 15, leading=None)
    p.setFillColorRGB(0.29296875, 0.453125, 0.609375)
    # 100, 100= width&height, 710 when increases goes up, when reduces comes down, 250=left padding
    p.drawImage(my_image, 250, 710, 100, 100)
    p.setFont("Helvetica", 10, leading=None)
    p.drawString(
        170, 700, "2nd Floor, Itiku House, MaCarthy Street, Onikan, Lagos")
    p.drawString(190, 680, "info@onigbanjo-oaiya.com | +234 01 342 4125")
    p.line(0, 670, 1000, 670)
    p.line(0, 672, 1000, 672)

    # Write content on the PDF
    p.setFont("Helvetica-Bold", 15, leading=None)
    p.drawString(20, 640, "Verification Report:")
    p.setFont("Helvetica", 10, leading=None)

    p1 = Paragraph('''<b>Ref No: </b> ''' +
                   selected_report.customer.ref_no, my_Style)
    p1.wrapOn(p, 500, 0)  # width & height
    p1.drawOn(p, width-575, height-235)

    p2 = Paragraph('''<b>Batch No: </b> ''' +
                   str(selected_report.customer.BATCH_NO), my_Style)
    p2.wrapOn(p, 500, 0)  # width & height
    p2.drawOn(p, width-575, height-255)

    p3 = Paragraph('''<b>Customer Name: </b> ''' + str(selected_report.customer.first_name) +
                   " " + str(selected_report.customer.last_name), my_Style)
    p3.wrapOn(p, 500, 0)  # width & height
    p3.drawOn(p, width-575, height-275)

    p4 = Paragraph('''<b>Customer Address: </b> ''' +
                   str(selected_report.customer.address), my_Style)
    p4.wrapOn(p, 500, 0)  # width & height
    p4.drawOn(p, width-575, height-315)

    p4 = Paragraph('''<b>City: </b> ''' +
                   str(selected_report.customer.city), my_Style)
    p4.wrapOn(p, 500, 0)  # width & height
    p4.drawOn(p, width-575, height-335)

    p5 = Paragraph('''<b>State: </b> ''' +
                   str(selected_report.customer.state), my_Style)
    p5.wrapOn(p, 500, 0)  # width & height
    p5.drawOn(p, width-575, height-355)

    p7 = Paragraph('''<b>Report Status: </b> ''' + status, my_Style)
    p7.wrapOn(p, 500, 0)  # width & height
    p7.drawOn(p, width-575, height-375)

    p8 = Paragraph('''<b>Verification Message: </b> ''' +
                   str(selected_report.VerificationMessage), my_Style)
    p8.wrapOn(p, 500, 0)  # width & height
    p8.drawOn(p, width-575, height-395)

    p9 = Paragraph('''<b>Building Condition: </b> ''' +
                   str(selected_report.buildingCondition), my_Style)
    p9.wrapOn(p, 500, 0)  # width & height
    p9.drawOn(p, width-575, height-415)

    p10 = Paragraph('''<b>Building Color: </b> ''' +
                    str(selected_report.buildingColor), my_Style)
    p10.wrapOn(p, 500, 0)  # width & height
    p10.drawOn(p, width-575, height-435)

    p11 = Paragraph('''<b>Building Type: </b> ''' +
                    str(selected_report.buildingType), my_Style)
    p11.wrapOn(p, 500, 0)  # width & height
    p11.drawOn(p, width-575, height-455)

    p12 = Paragraph('''<b>Customer Relationship With Address: </b> ''' +
                    str(selected_report.CustomerRelationshipWithaddress), my_Style)
    p12.wrapOn(p, 500, 0)  # width & height
    p12.drawOn(p, width-575, height-475)

    p13 = Paragraph('''<b>Address Residential: </b> ''' +
                    str(selected_report.AddressResidential), my_Style)
    p13.wrapOn(p, 500, 0)  # width & height
    p13.drawOn(p, width-575, height-495)

    p14 = Paragraph('''<b>Name of individual Interviewed: </b> ''' +
                    str(selected_report.NameofindividualInterviewed), my_Style)
    p14.wrapOn(p, 500, 0)  # width & height
    p14.drawOn(p, width-575, height-515)

    p15 = Paragraph('''<b>Relationship With Customer: </b> ''' +
                    str(selected_report.RelationshipWithCustomer), my_Style)
    p15.wrapOn(p, 500, 0)  # width & height
    p15.drawOn(p, width-575, height-535)

    p16 = Paragraph('''<b>Landmark: </b> ''' +
                    str(selected_report.Landmark), my_Style)
    p16.wrapOn(p, 500, 0)  # width & height
    p16.drawOn(p, width-575, height-555)

    p17 = Paragraph('''<b>Agent: </b> ''' +
                    str(selected_report.agent), my_Style)
    p17.wrapOn(p, 500, 0)  # width & height
    p17.drawOn(p, width-575, height-575)

    p18 = Paragraph('''<b>Client: </b> ''' +
                    str(selected_report.customer.client), my_Style)
    p18.wrapOn(p, 500, 0)  # width & height
    p18.drawOn(p, width-575, height-595)

    p19 = Paragraph('''<b>Date: </b> ''' +
                    str(selected_report.created_at.strftime("%m/%d/%Y, %I:%M%p")), my_Style)
    p19.wrapOn(p, 500, 0)  # width & height
    p19.drawOn(p, width-575, height-615)

    p20 = Paragraph('''<b>TAT : </b> ''' +
                    str(selected_report.TAT) + " hrs", my_Style)
    p20.wrapOn(p, 500, 0)  # width & height
    p20.drawOn(p, width-575, height-635)

    p21 = Paragraph('''<b>Client Job Ref Number: </b> ''' +
                    str(selected_report.clientJobrefID), my_Style)
    p21.wrapOn(p, 500, 0)  # width & height
    p21.drawOn(p, width-575, height-655)

    p22 = Paragraph('''<b>More Comment by Agent: </b> ''' +
                    str(selected_report.MoreComment), my_Style)
    p22.wrapOn(p, 500, 0)  # width & height
    p22.drawOn(p, width-575, height-715)

    p.drawString(200, 30, f'Generated: {today.strftime("%m/%d/%Y, %I:%M%p")}')

    # Finish Up
    p.setTitle(f'Report on {today.strftime("%m/%d/%Y, %I:%M%p")}')
    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


# staff profile
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def staffprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    Staffdetails_inusertable = User.objects.get(
        email__exact=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(
            request.POST,  request.FILES, instance=profile)
        user_form = UserProfileUpdateForm(
            request.POST,  request.FILES, instance=Staffdetails_inusertable)
        if profile_form.is_valid() and user_form.is_valid():
            profile_form.save()
            user_form.save()
            messages.success(request, 'Account Profile Details was updated.')
            return redirect('staffprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)

    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserProfileUpdateForm(instance=Staffdetails_inusertable)

    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'profile': profile,
    }
    return render(request, 'staffs/users/profile.html', context)


# ==================================OutstandingReport=======================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def OutstandingReport(request):
    no_reports_found = False  # Initialize the variable to False

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('latin-1').splitlines()
        csv_reader = csv.DictReader(decoded_file)

        # Collect all CIFs and ActivityIDs from the CSV
        cifs = []
        activity_ids = []

        for row in csv_reader:
            cif = row.get('CIF', '').strip()
            activity_id = row.get('ActivityId', '').strip()

            if cif:
                cifs.append(cif)
            if activity_id:
                activity_ids.append(activity_id)

        # Bulk query for all matching reports
        matched_reports = Report.objects.filter(
            Q(clientJobrefID__in=cifs) | Q(clientJobrefID__in=activity_ids)
        ).distinct()

        # Generate PDF URLs for matched reports
        for report in matched_reports:
            try:
                pdf_url = reverse('reportinPdf', kwargs={'pk': report.pk})
                report.pdf_url = request.build_absolute_uri(pdf_url)
            except Exception:
                report.pdf_url = ''  # Handle exception if PDF generation fails

        current_domain = request.build_absolute_uri('/')[:-1]

        if not matched_reports:  # Check if no reports are found
            no_reports_found = True

        return render(request, 'feedbacks/OutstandingReports.html', {
            'reports': matched_reports,
            'current_domain': current_domain,
            'no_reports_found': no_reports_found
        })

    return render(request, 'feedbacks/OutstandingReports.html')



# ========================Search by Address for Reports- Urgent Reports=========================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def searchbyaddress(request):
    no_reports_found = False  # Initialize the variable to False

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('latin-1').splitlines()
        csv_reader = csv.DictReader(decoded_file)

        # Collect all Addresses and CIFs from the CSV
        addresses = []
        cifs = []

        for row in csv_reader:
            address = row.get('Address', '').strip()
            cif = row.get('CIF', '').strip()

            if address:
                addresses.append(address)
            if cif:
                cifs.append(cif)

        # Bulk query for all matching reports
        matched_reports = Report.objects.filter(
            Q(address__in=addresses) | Q(clientJobrefID__in=cifs)
        ).distinct()

        # Generate PDF URLs for matched reports
        for report in matched_reports:
            try:
                pdf_url = reverse('reportinPdf', kwargs={'pk': report.pk})
                report.pdf_url = request.build_absolute_uri(pdf_url)
            except Exception:
                report.pdf_url = ''  # Handle exception if PDF generation fails

        current_domain = request.build_absolute_uri('/')[:-1]

        if not matched_reports:  # Check if no reports are found
            no_reports_found = True

        return render(request, 'feedbacks/UrgentReport.html', {
            'reports': matched_reports,
            'current_domain': current_domain,
            'no_reports_found': no_reports_found
        })

    return render(request, 'feedbacks/UrgentReport.html')
##########################################################################################

# ====================== confirm addresses not sent to portal============================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def ConfirmJobnotsent(request):
    no_jobs_found = False  # Initialize the variable to False

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('latin-1').splitlines()
        csv_reader = csv.DictReader(decoded_file)

        # Collect all ActivityIDs and CIFs from the CSV
        activity_ids = []
        cifs = []
        jobs_from_csv = []

        for row in csv_reader:
            if 'ActivityId' not in row or 'CIF' not in row:
                continue  # Skip the row if any required fields are missing

            ActivityID = row.get('ActivityId')
            CIF = row.get('CIF')

            activity_ids.append(ActivityID)
            cifs.append(CIF)

        # Perform a bulk query to get all jobs that exist in the database
        existing_jobs = set(Job.objects.filter(
            Q(clientJobrefID__in=activity_ids) | Q(clientJobrefID__in=cifs)
        ).values_list('clientJobrefID', flat=True))

        # Rewind the CSV reader to process it again
        csv_reader = csv.DictReader(decoded_file)  # Re-initialize the csv_reader

        # Process the CSV again, filtering out jobs that exist
        for row in csv_reader:
            ActivityID = row.get('ActivityId')
            CIF = row.get('CIF')

            # Check if the job is not in the existing jobs set
            if ActivityID not in existing_jobs and CIF not in existing_jobs:
                jobs_from_csv.append(row)

        if not jobs_from_csv:  # Check if no jobs are found
            no_jobs_found = True

        return render(request, 'feedbacks/NotFoundjobs.html', {'jobs_from_csv': jobs_from_csv, 'no_jobs_found': no_jobs_found})

    return render(request, 'feedbacks/NotFoundjobs.html')


# ===========================================JobStatisticsView==================================
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def JobStatisticsView(request):
    clients = Client.objects.all()
    job_statistics = []

    for client in clients:
        pending_jobs = Job.objects.filter(client=client, status='0')
        unassigned_jobs = Job.objects.filter(
            client=client, agent__isnull=True)
        rejected_jobs = Job.objects.filter(client=client, status='2')
        done_jobs = Job.objects.filter(client=client, status='1')

        # Get total jobs created in the current month
        current_month = datetime.now().month
        current_year = datetime.now().year
        current_month_jobs = Job.objects.filter(
            client=client,
            created_at__year=current_year,
            created_at__month=current_month
        ).count()

        # Get monthly job assignments
        monthly_assignments = Job.objects.filter(
            client=client,
            created_at__year=current_year,
            created_at__month=current_month
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(total_jobs=Count('id'))

        # Overall total jobs for the client
        overall_total_jobs = Job.objects.filter(client=client).count()

        job_statistics.append({
            'client': client,
            'pending_jobs_count': pending_jobs.count(),
            'unassigned_jobs_count': unassigned_jobs.count(),
            'rejected_jobs_count': rejected_jobs.count(),
            'done_jobs_count': done_jobs.count(),
            'current_month_jobs': current_month_jobs,
            'monthly_assignments': monthly_assignments,
            'overall_total_jobs': overall_total_jobs,
        })

    context = {'job_statistics': job_statistics}
    return render(request, 'statistics/job_statistics.html', context)
# ===========================GET STATISTICS OF REPORTS====================
# ==========================================ReportStatisticsView================================


@login_required(login_url='login')
@user_passes_test(check_role_staff)
def ReportStatisticsView(request):
    clients = Client.objects.all()
    report_statistics = []

    for client in clients:
        # Pending, Approved, Rejected Reports
        pending_reports = Report.objects.filter(
            Client=client, Reportstatus='0')
        approved_reports = Report.objects.filter(
            Client=client, Reportstatus='1')
        rejected_reports = Report.objects.filter(
            Client=client, Reportstatus='2')

        # Today's Approved Reports
        today_approved_reports = approved_reports.filter(
            created_at__date=timezone.now().date()
        )

        # Month's Approved Reports
        month_approved_reports = approved_reports.filter(
            created_at__month=timezone.now().month, created_at__year=timezone.now().year
        )

        report_statistics.append({
            'client': client,
            'pending_reports_count': pending_reports.count(),
            'rejected_reports_count': rejected_reports.count(),
            'today_approved_reports_count': today_approved_reports.count(),
            'month_approved_reports_count': month_approved_reports.count(),
            'total_approved_reports_count': approved_reports.count(),
        })

    context = {'report_statistics': report_statistics}
    return render(request, 'statistics/report_statistics.html', context)




##################### search_reports( #################################################
@login_required(login_url='login')
@user_passes_test(check_role_staff)
def search_reports(request):
    no_reports_found = False

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('latin-1').splitlines()
        csv_reader = csv.DictReader(decoded_file)

        search_criteria = request.POST.get('search_criteria')

        # Collect search values from the CSV file based on the selected search criteria
        activity_ids = []
        fullnames = []
        addresses = []
        cifs = []

        for row in csv_reader:
            if search_criteria in ['ActivityId', 'clientJobrefID_address_customer_name_CIF']:
                activity_ids.append(row.get('ActivityId', '').strip())

            if search_criteria in ['fullname', 'address_customer_name', 'clientJobrefID_address_customer_name_CIF']:
                fullnames.append(row.get('fullname', '').strip())

            if search_criteria in ['Address', 'clientJobrefID_address', 'address_customer_name', 'clientJobrefID_address_customer_name_CIF']:
                addresses.append(row.get('Address', '').strip())

            if search_criteria in ['CIF', 'clientJobrefID_address_customer_name_CIF']:
                cifs.append(row.get('CIF', '').strip())

        # Construct a Q object to perform a single query based on the search criteria
        query = Q()

        if search_criteria == 'ActivityId':
            query &= Q(clientJobrefID__in=activity_ids)
        elif search_criteria == 'fullname':
            query &= Q(customer__first_name__in=[fn.split(maxsplit=1)[0] for fn in fullnames if ' ' in fn]) | \
                     Q(customer__last_name__in=[fn.split(maxsplit=1)[1] for fn in fullnames if ' ' in fn])
        elif search_criteria == 'Address':
            query &= Q(address__in=addresses)
        elif search_criteria == 'clientJobrefID_address':
            query &= Q(clientJobrefID__in=activity_ids) & Q(address__in=addresses)
        elif search_criteria == 'address_customer_name':
            query &= Q(address__in=addresses) & \
                     (Q(customer__first_name__in=[fn.split(maxsplit=1)[0] for fn in fullnames if ' ' in fn]) |
                      Q(customer__last_name__in=[fn.split(maxsplit=1)[1] for fn in fullnames if ' ' in fn]))
        elif search_criteria == 'clientJobrefID_address_customer_name_CIF':
            query &= Q(clientJobrefID__in=activity_ids) & Q(address__in=addresses) & \
                     (Q(customer__first_name__in=[fn.split(maxsplit=1)[0] for fn in fullnames if ' ' in fn]) |
                      Q(customer__last_name__in=[fn.split(maxsplit=1)[1] for fn in fullnames if ' ' in fn])) & \
                     Q(clientJobrefID__in=cifs)
        elif search_criteria == 'CIF':
            query &= Q(clientJobrefID__in=cifs)

        # Execute the query once, instead of multiple times
        matched_reports = Report.objects.filter(query).distinct()

        current_domain = request.build_absolute_uri('/')[:-1]

        if not matched_reports.exists():  # Check if no reports are found
            no_reports_found = True

        return render(request, 'feedbacks/searchReports.html', {
            'reports': matched_reports,
            'current_domain': current_domain,
            'no_reports_found': no_reports_found
        })

    return render(request, 'feedbacks/searchReports.html')



class ApprovalAndSendTemplateView(TemplateView):
    template_name = 'feedbacks/processBulkapproval.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['approval_status'] = False
        context['success_count'] = 0
        context['not_found_count'] = 0
        context['not_sent_count'] = 0
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            csv_file = request.FILES['csv_file']

            current_datetime = timezone.now().strftime("%Y-%m-%d %H:%M:%S.%f%z")
            success_count = 0
            not_found_count = 0
            not_sent_count = 0
            error_messages = []

            try:
                decoded_file = csv_file.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)

                for row in reader:
                    # Convert to lowercase
                    activity_id = row.get('ActivityId', '').strip().lower()
                    # Leave address as is
                    address = row.get('Address', '')

                    # Fetch report details based on ActivityId and Address (case-insensitive)
                    report = Report.objects.filter(
                        clientJobrefID__iexact=activity_id,  # Case-insensitive lookup for ActivityId
                        address=address
                    ).first()

                    if report:
                        try:
                            payload = {
                                "ActivityId": report.clientJobrefID,
                                "CustomerName": f"{report.customer.first_name} {report.customer.last_name}",
                                "VerificationAddress": report.address,
                                "VisitDate": report.created_at.strftime("%b. %d, %Y"),
                                "VendorId": "6ce5c941-63c6-4da0-9639-dc7554d0a024",
                                "AddressExist": report.VerificationMessage == 'Address exists and customer is known',
                                "AddressResidential": report.AddressResidential == 'Yes',
                                "CustomerResident": report.AddressResidential == 'Yes',
                                "CustomerKnown": report.VerificationMessage == 'Address exists and customer is known',
                                "MetWith": "N/A",
                                "EaseOfLocation": "No",
                                "Comments": report.MoreComment,
                                "ReceivedDate": report.created_at.strftime("%b. %d, %Y"),
                                "VisitTime": report.created_at.strftime("%I:%M %p"),
                                "PersonMetOthers": report.RelationshipWithCustomer,
                                "NameOfPersonMet": report.RelationshipWithCustomer,
                                "VisitFeedback": "Passed" if report.VerificationMessage == 'Address exists and customer is known' else "Failed",
                                "AddressImage": [
                                    {
                                        "CustomerId": "N/A",
                                        "FileName": "N/A",
                                        "FileType": "N/A",
                                        "ImageUrl": report.photo1.url if report.photo1 else "N/A"
                                    }
                                ]
                            }

                            api_url = 'https://apibox.alat.ng/digitaloperationsonboarding/api/addressVerification/AddressVerificationResponse'
                            headers = {'Content-Type': 'application/json'}

                            response = requests.post(
                                api_url, data=json.dumps(payload), headers=headers)

                            if response.status_code == 200:
                                api_response = response.json()
                                print("Success Message:", api_response.get(
                                    "message", "API response message not found"))
                                # Mark report as approved
                                report.Reportstatus = '1'  # Update to 'Approved'
                                report.modified_at = current_datetime
                                report.approvedBy = request.user
                                report.save()
                                success_count += 1
                            else:
                                not_sent_count += 1
                                error_messages.append(
                                    f"Failed to send report {report.clientJobrefID} to API. Status code: {response.status_code}")
                                # Mark report as not approved
                                report.Reportstatus = '0'
                                report.save()

                        except Exception as e:
                            not_sent_count += 1
                            error_messages.append(
                                f"Exception occurred while processing report {report.clientJobrefID}: {str(e)}")
                            # Mark report as not approved
                            report.Reportstatus = '0'
                            report.save()

                    else:
                        not_found_count += 1
                        error_messages.append(
                            f"Report with ActivityId '{activity_id}' and Address '{address}' not found in database.")

            except Exception as e:
                error_messages.append(f"Error processing CSV file: {str(e)}")

            context = {
                'approval_status': True,
                'success_count': success_count,
                'not_found_count': not_found_count,
                'not_sent_count': not_sent_count,
                'error_messages': error_messages
            }
            return render(request, self.template_name, context)

        else:
            context = {
                'approval_status': False,
                'form': form  # Pass the form instance to re-render with errors
            }
            return render(request, self.template_name, context)
