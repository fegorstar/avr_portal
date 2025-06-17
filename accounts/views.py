from django.shortcuts import get_object_or_404, redirect, render
from django.http.response import HttpResponse
from .models import User, UserProfile
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import detectUser
from django.core.exceptions import PermissionDenied
from .forms import UserProfileForm
from datetime import datetime

from staffs.models import Agent, Job, Client, Report
from django.db.models import Q


# for webapi
from rest_framework.generics import GenericAPIView
from .serializers import UserSerializer, LoginSerializer
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import jwt


# Restrict other from accessing the staff page
def check_role_staff(user):
    if user.role == 1:
        return True
    else:
        raise PermissionDenied

# Restrict others from accessing the client page


def check_role_agent(user):
    if user.role == 2:
        return True
    else:
        raise PermissionDenied

# Restrict others from accessing the agent page


def check_role_client(user):
    if user.role == 3:
        return True
    else:
        raise PermissionDenied


# login
def login(request):
    # checking that the user is already loggedin
    if request.user.is_authenticated:
        # messages.warning(request, 'You are already logged in!')
        return redirect('myAccount')
    elif request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('myAccount')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')
    return render(request, 'accounts/login.html')


# logout
def logout(request):
    auth.logout(request)
    messages.info(request, 'You are logged out.')
    return redirect('login')

from django.utils import timezone

@login_required(login_url='login')
def myAccount(request):
    # request.user is the current loggedin user
    user = request.user
    redirectUrl = detectUser(user)
    return redirect(redirectUrl)

@login_required(login_url='login')
@user_passes_test(check_role_staff)
def staffDashboard(request):
    # Get the user profile of the logged-in user and pass to the template
    profile = get_object_or_404(UserProfile, user=request.user)
    profile_form = UserProfileForm(instance=profile)

    # Get total number of agents and clients
    total_no_of_agents = Agent.objects.all().count()
    total_no_of_clients = Client.objects.all().count()

    # Get jobs
    unassigned_jobs = Job.objects.filter(agent=None, status=0, published=1).count()
    totalcompletedjobs = Job.objects.filter(status=1).exclude(agent=None).count()
    Rejected_jobs = Job.objects.filter(status=2).count()
    undone_jobs = Job.objects.filter(status=0).exclude(agent=None).count()

    # My Reports
    PendingReports = Report.objects.filter(Reportstatus=0).count()
    ApprovedReports = Report.objects.filter(Reportstatus=1).count()
    RejectedReports = Report.objects.filter(Reportstatus=2).count()

    now = timezone.now()
    todaysReport = Report.objects.filter(Reportstatus=1, modified_at__date=now.date()).count()

    current_month = now.month
    current_year = now.year
    current_month_reports = Report.objects.filter(
        Reportstatus=1,
        created_at__month=current_month,
        created_at__year=current_year
    ).count()

    context = {
        'profile_form': profile_form,
        'profile': profile,
        'total_no_of_agent': total_no_of_agents,
        'total_no_of_clients': total_no_of_clients,
        'totalcompletedjobs': totalcompletedjobs,
        'unassigned_jobs': unassigned_jobs,
        'Rejected_jobs': Rejected_jobs,
        'PendingReports': PendingReports,
        'ApprovedReports': ApprovedReports,
        'RejectedReports': RejectedReports,
        'todaysReport': todaysReport,
        'current_month_reports': current_month_reports,
        'undone_jobs': undone_jobs,
    }
    return render(request, 'accounts/staffDashboard.html', context)


# get the agent that is loggedin
def get_agent(request):
    agent = Agent.objects.get(user=request.user)
    return agent


@login_required(login_url='login')
@user_passes_test(check_role_agent)
def agentDashboard(request):
    # get the userprofile of the loggedin user and pass to the template
    profile = get_object_or_404(UserProfile, user=request.user)
    agent = get_agent(request)

    # get all agent's assigned Jobs
    Mytotal_no_ofassigned_jobs = Job.objects.filter(agent=agent).count()
    MyUndone_jobs = Job.objects.filter(agent=agent, status=0).count()
    MyDone_jobs = Job.objects.filter(agent=agent, status=1).count()
    MyRejected_jobs = Job.objects.filter(agent=agent, status=2).count()

    # My Reports
    MyApprovedReports = Report.objects.filter(
        agent=agent, Reportstatus=1). count()
    MyRejectedReports = Report.objects.filter(
        agent=agent, Reportstatus=2).count()

    context = {
        'profile': profile,
        'agent': agent,
        'Mytotal_no_ofassigned_jobs': Mytotal_no_ofassigned_jobs,
        'MyUndone_jobs': MyUndone_jobs,
        'MyDone_jobs': MyDone_jobs,
        'MyRejected_jobs': MyRejected_jobs,
        'MyApprovedReports': MyApprovedReports,
        'MyRejectedReports': MyRejectedReports,
    }
    return render(request, 'accounts/agentDashboard.html', context)


# CLIENT SECTION
@login_required(login_url='login')
@user_passes_test(check_role_client)
def clientDashboard(request):
    # get the userprofile of the loggedin user and pass to the template
    profile = get_object_or_404(UserProfile, user=request.user)
    client = get_object_or_404(Client, user=request.user)
    client_id = client.id
    print(client)

    # Get client rejected Jobs
    Rejected_jobs = Job.objects.filter(client=client, status=2).all().count()
    # Get client undone requests Jobs
    UndoneRequests = Job.objects.filter(client=client, status=0).all().count()

    # Get client undone requests Jobs
    DoneRequests = Job.objects.filter(client=client, status=1).all().count()

    # Clients Reports
    PendingReports = Report.objects.filter(
        Client=client, Reportstatus=0).all().count()
    ApprovedReports = Report.objects.filter(
        Client=client, Reportstatus=1).all().count()
    RejectedReports = Report.objects.filter(
        Client=client, Reportstatus=2).all().count()

    today = datetime.now()
    # print (today)
    todaysReport = Report.objects.filter(Client=client,
                                         Reportstatus=1, modified_at__date=today).count()

    current_month = datetime.now().strftime('%m')
    # print(current_month)
    current_month_reports = Report.objects.filter(Client=client,
                                                  Reportstatus=1, created_at__month=current_month).count()

    context = {
        'profile': profile,
        'client': client,
        'client_id': client_id,
        'Rejected_jobs': Rejected_jobs,
        'PendingReports': PendingReports,
        'ApprovedReports':  ApprovedReports,
        'RejectedReports': RejectedReports,
        'todaysReport': todaysReport,
        'current_month_reports': current_month_reports,
        'UndoneRequests': UndoneRequests,
        'DoneRequests': DoneRequests

    }
    return render(request, 'accounts/clientDashboard.html', context)
