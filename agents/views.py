from django.db import transaction, IntegrityError
from dateutil import parser as date_parser
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import User,  UserProfile
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import check_role_agent
from staffs.models import Agent, Job, Report
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from geopy.geocoders import Nominatim
from staffs.forms import EditJobForm, ReportJobForm, JobForm, ImportReportForm,  uploadReportForm
from .forms import AgentuserForm, AgentForm, EditReportForm
from accounts.forms import UserProfileForm, UserProfileUpdateForm
from django.contrib import messages, auth
from django.http import HttpResponse, JsonResponse
import csv
import requests
import json
from django.views.decorators.http import require_POST


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from staffs.filters import JobFilter, ReportFilter
from django.urls import reverse

from dateutil import parser
from django.utils import timezone
import datetime
from datetime import datetime

# Libraries For the bulk reports uploads
from django.views.generic.base import View
from csv import DictReader
from io import TextIOWrapper
from django.utils.timesince import timesince

from staffs.views import reportinPdf
from django.core.files.base import ContentFile


# get the agent that is loggedin
def get_agent(request):
    agent = Agent.objects.get(user=request.user)
    return agent


# ===================================Assigned Jobs=====================================
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def agentassignedjobs(request):
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    agent = get_agent(request)

    # get all agent's assigned Jobs which are undone
    Mytotal_no_ofassigned_jobs = Job.objects.filter(
        agent=agent, status=0).order_by('-created_at').count()
    context = {
        'profile': profile,
        'agent': agent,
        'Mytotal_no_ofassigned_jobs': Mytotal_no_ofassigned_jobs,
    }
    return render(request, 'agents/assignedjobs.html', context)


# ----------------------FETCH JOB DATA INTO THE DATATABLE IN UNASSIGNED JOBS PAGE
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def fetch_agentunassignedjobs(request):
    agent = get_agent(request)
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    columns = ['ref_no', 'clientJobrefID', 'first_name', 'last_name', 'address',
               'state', 'city', 'client__client_name', 'created_at', 'agent__fullname']

    filter_criteria = Q(agent=agent, status=0, published=1)

    if search_value:
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        if ' ' in search_value:
            first_name, last_name = search_value.split(' ', 1)
            search_filter |= (Q(first_name__icontains=first_name)
                              & Q(last_name__icontains=last_name))
        filter_criteria &= search_filter

    data = Job.objects.filter(filter_criteria).order_by('-created_at')
    records_total = Job.objects.count()
    records_filtered = data.count()

    paginator = Paginator(data, length)
    page_number = (start // length) + 1
    data_page = paginator.page(page_number)

    data = [
        {
            'id': item.id,
            'jobrefno': item.ref_no,
            'clientJobrefID': item.clientJobrefID,
            'customerName': f"{item.first_name or 'N/A'} {item.last_name or 'N/A'}",
            'address': item.address if item.address else 'N/A',
            'state': item.state if item.state else 'N/A',
            'city': item.city if item.city else 'N/A',
            'client': item.client.client_name if item.client else 'N/A',
            'agent': item.agent.fullname if item.agent and hasattr(item.agent, 'fullname') else 'N/A',
            'created_at': timezone.localtime(item.created_at).strftime('%Y-%m-%d %I:%M:%S %p') if item.created_at else 'N/A',
            'whenAssigned': timezone.localtime(item.whenAssigned).strftime('%b. %d, %Y, %I:%M %p') if item.whenAssigned else 'N/A',
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


# View Job details
# ---------------------------fetch job details section-------------------------
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def fetch_job_detailsagentsection(request):
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


# ===============================Address Report===================================

@login_required(login_url='login')
@user_passes_test(check_role_agent)
def Address_Report(request, pk):
    selected_job = get_object_or_404(Job, pk=pk)
    agent = get_object_or_404(Agent, user=request.user)
    nowseleted = selected_job.ref_no  # Store the job reference number for status update

    if request.method == 'POST':
        # Process the form data and capture latitude and longitude
        Reportform = ReportJobForm(request.POST, request.FILES)

        try:
            if Reportform.is_valid():
                # Fetch first_name and last_name from the Job instance to build customer name
                first_name = selected_job.first_name
                last_name = selected_job.last_name
                full_name = f"{first_name} {last_name}"

                # Get latitude and longitude from the form
                latitude = request.POST.get('latitude')
                longitude = request.POST.get('longitude')

                # Ensure that latitude and longitude are provided
                if not latitude or not longitude:
                    messages.error(request, 'Location verification is required. Please enable location services or enter the address manually.')
                    return redirect('reportAddress', pk=pk)

                # Date and time handling for job assigned and report creation
                current_datetime = str(datetime.now())
                date_format1 = parser.parse(current_datetime)
                whenJobAssigned_str = str(request.POST['whenJobAssigned'])
                if 'midnight' in whenJobAssigned_str:
                    whenJobAssigned_str = whenJobAssigned_str.replace('midnight', '12:00am')
                elif 'noon' in whenJobAssigned_str:
                    whenJobAssigned_str = whenJobAssigned_str.replace('noon', '12:00pm')

                date_format2 = date_parser.parse(whenJobAssigned_str)
                diff = date_format1 - date_format2  # Calculate difference
                total_TAT = diff.total_seconds() / 60 / 60  # TAT in hours

                # Get other fields from the form
                JobRefNo = request.POST['JobRefNo']
                clientJobrefID = request.POST['clientJobrefID']
                client = request.POST['client']
                buildingCondition = Reportform.cleaned_data['buildingCondition']
                buildingColor = Reportform.cleaned_data['buildingColor']
                buildingType = Reportform.cleaned_data['buildingType']
                CustomerRelationshipWithaddress = Reportform.cleaned_data['CustomerRelationshipWithaddress']
                AddressResidential = Reportform.cleaned_data['AddressResidential']
                NameofindividualInterviewed = Reportform.cleaned_data['NameofindividualInterviewed']
                RelationshipWithCustomer = Reportform.cleaned_data['RelationshipWithCustomer']
                VerificationMessage = Reportform.cleaned_data['VerificationMessage']
                MoreComment = Reportform.cleaned_data['MoreComment']
                Landmark = Reportform.cleaned_data['Landmark']
                address = Reportform.cleaned_data['address']
                photo1 = Reportform.cleaned_data['photo1']

                # Save the report object with captured geolocation data
                reportjob = Reportform.save(commit=False)  # Prepare to save the report object
                reportjob.customer = selected_job
                reportjob.agent = agent
                reportjob.TAT = total_TAT
                reportjob.Reportstatus = 0  # Default report status
                reportjob.JobRefNo = JobRefNo
                reportjob.address = address  # Save the address
                reportjob.clientJobrefID = clientJobrefID  # Save client reference ID
                reportjob.Client = client
                reportjob.created_at = date_format1
                reportjob.modified_at = date_format1
                reportjob.customerName = full_name
                reportjob.latitude = latitude  # Save the latitude
                reportjob.longitude = longitude  # Save the longitude
                reportjob.save()

                # After saving the report, update the job status
                jobstatus = Job.objects.filter(ref_no=nowseleted).update(status=1)

                # Success message
                messages.success(request, 'Report successfully submitted!')
                return redirect('agentassignedjobs')

        except IntegrityError:
            messages.error(request, 'You have already added a report for this job!')
    else:
        # If GET request, instantiate the empty form
        Reportform = ReportJobForm()

    context = {
        'selected_job': selected_job,
        'Reportform': Reportform,
        'agent': agent,
    }

    return render(request, 'agents/AddressreportForm.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_agent)
def reject_job(request, job_id):
    if request.method == 'POST':
        try:
            job = Job.objects.get(id=job_id)
            job.status = 2  # Set the status to 'Rejected'
            job.save()
            return JsonResponse({'message': 'Job rejected successfully'})
        except Job.DoesNotExist:
            return JsonResponse({'message': 'Job not found'}, status=404)
    return JsonResponse({'message': 'Invalid request method'}, status=400)


# ================================Reports section=================================
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def agentreport(request):
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    agent = get_agent(request)

    # get all agent's assigned Jobs
    Mytotal_no_of_reports = Report.objects.filter(
        agent=agent).order_by('created_at').count()
    context = {
        'profile': profile,
        'agent': agent,
        'Mytotal_no_of_reports': Mytotal_no_of_reports,
    }
    return render(request, 'agents/my_reports.html', context)


# ------------------fetch all reportdata-------------------------
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def fetchagentreportdata(request):
    agent = get_agent(request)
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus',
               'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']

    filter_criteria = Q(agent=agent)

    if search_value:
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        filter_criteria &= search_filter

    data = Report.objects.filter(filter_criteria).order_by('-created_at')

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
            'customerName': f"{item.customerName or 'N/A'}",
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


@login_required(login_url='login')
@user_passes_test(check_role_agent)
def fetchagentreportdetails(request):
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

          

            # Prepare the data to send as JSON response
            data = {
                'downloadLink': download_link,  # Include the download link
                'id': job.pk,
                'client': job.Client,
                'agent': job.agent,
                'clientrefNo': job.clientJobrefID,
                'name': customerName,
                'customeraddress': job.address,
                'latitude': job.latitude,
                'longitude': job.longitude,
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


# ==========================Agent Edit Report====================
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def EditReport(request, pk=None):
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
            return redirect('myreport')

        else:
            print('invalid form')
            print(Reportform.errors)

    else:
        Reportform = EditReportForm(instance=selected_report)

    context = {
        'selected_report': selected_report,
        'Reportform': Reportform,
    }
    return render(request, 'agents/EditReportForm.html', context)
# ======================================EXPORT TO CSV REPORTS=================================


# ==============================================Rejected Reports=================================
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def agentrejectedreports(request):
    # To show loggedin Userprofile -sho is adding job
    profile = get_object_or_404(UserProfile, user=request.user)
    agent = get_agent(request)
    # get all reports
    totalrejected_no_of_reports = Report.objects.filter(
        Reportstatus=2, agent=agent).order_by('created_at').count()

    context = {
        'profile': profile,
        'totalrejected_no_of_reports': totalrejected_no_of_reports,
    }
    return render(request, 'agents/rejectedreports.html', context)


# ================FETCH REJECTED REPORTS==============
@login_required(login_url='login')
@user_passes_test(check_role_agent)
def fetch_agentrejectedreportdata(request):
    agent = get_agent(request)
    draw = request.GET.get('draw', 1)
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]')

    columns = ['customer__ref_no', 'customer__first_name', 'customer__last_name', 'clientJobrefID', 'address', 'Reportstatus',
               'VerificationMessage', 'TAT', 'Client', 'agent', 'created_at']

    filter_criteria = Q(Reportstatus=2, agent=agent)

    if search_value:
        search_filter = Q()
        for column in columns:
            search_filter |= Q(**{f'{column}__icontains': search_value})
        filter_criteria &= search_filter

    data = Report.objects.filter(filter_criteria).order_by('-created_at')

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
            'JobRefNo': item.JobRefNo,
            'clientJobrefID': item.clientJobrefID,
            'customerName': f"{item.customer.first_name or 'N/A'} {item.customer.last_name or 'N/A'}",
            'address': item.address if item.address else 'N/A',
            'client': item.Client if item.Client else 'N/A',
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
@user_passes_test(check_role_agent)
def EditagentRejectedReport(request, pk=None):
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
            return redirect('agentrejectedreports')

        else:
            print('invalid form')
            print(Reportform.errors)

    else:
        Reportform = EditReportForm(instance=selected_report)

    context = {
        'selected_report': selected_report,
        'Reportform': Reportform,
    }
    return render(request, 'agents/EditRejectedform.html', context)
# ==================================End of EditRejectedReport=============================


class UploadReportViewbyagent(View):
    def get(self, request, *args, **kwargs):
        # Prevent access to the page if not an agent
        if request.user.is_authenticated and request.user.role == User.AGENT:
            agent = get_object_or_404(Agent, user=request.user)
            context = {
                "form": ImportReportForm(),
                'agent': agent,
            }
            return render(request, 'agents/reportupload.html', context)
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
        return render(request, 'agents/reportupload.html', context)


@login_required(login_url='login')
@user_passes_test(check_role_agent)
def agentprofile(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    agentContactDetails = User.objects.get(
        email__exact=request.user)
    agent = get_object_or_404(Agent, user=request.user)

    if request.method == 'POST':
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=profile)
        user_form = AgentuserForm(
            request.POST,  request.FILES, instance=agentContactDetails)

        agent_form = AgentForm(
            request.POST,  request.FILES, instance=agent)

        if profile_form.is_valid() and user_form.is_valid() and agent_form.is_valid():
            profile_form.save()
            user_form.save()
            agent_form.save()
            messages.success(request, 'Account Profile Details was updated.')
            return redirect('agentprofile')
        else:
            print(profile_form.errors)
            print(user_form.errors)
            print(agent_form.errors)

    else:
        profile_form = UserProfileForm(instance=profile)
        user_form = UserProfileUpdateForm(instance=agentContactDetails)
        agent_form = AgentForm(instance=agent)

    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'agent_form': agent_form,
        'agent': agent  # can access contactdetails and profile from here

    }

    return render(request, 'agents/profile.html', context)


# Export to CSV Jobs
def export_csv(request):
    # To show loggedin Userprofile -sho is adding job
    agent = get_agent(request)
    current_datetime = str(datetime.now())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'inline; filename="{agent} Pending Jobs- {current_datetime}.csv"'
    writer = csv.writer(response)
    writer.writerow(['customer', 'clientJobrefID', 'first_name', 'last_name', 'email',
                    'phone_number', 'address', 'state', 'city', 'whenAssigned', 'BATCH_NO', 'VerificationMessage', 'buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential', 'NameofindividualInterviewed', 'RelationshipWithCustomer', 'MoreComment', 'Landmark'])  # CSV header

    # get all agent's assigned Jobs which are undone
    Myassigned_jobs = Job.objects.filter(
        agent=agent, status=0).order_by('-created_at')

    my_Filter = JobFilter(request.GET, queryset=Myassigned_jobs)
    all_jobs = my_Filter.qs

    for job in all_jobs:
        writer.writerow([job.ref_no, job.clientJobrefID, job.first_name, job.last_name,
                        job.email, job.phone_number, job.address,  job.state, job.city, job.whenAssigned, job.BATCH_NO])
    return response
