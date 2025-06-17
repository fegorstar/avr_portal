from django.urls import path, include
from . import views
from clients.views import ClientImportView

urlpatterns = [

    # Client side
    path('clientprofile/', views.clientprofile, name='clientprofile'),

    # Client Job CRUDS.
    path('clientjobs/', views.jobs, name='clientjobs'),
    path('fetchclientjob_data/', views.fetchclientjob_data,
         name='fetchclientjob_data'),
    path('clientedit_job_details/', views.clientedit_job_details,
         name='clientedit_job_details'),
    path('clientupdate_job/', views.clientupdate_job, name='clientupdate_job'),
    path('clientdelete_job/', views.clientdelete_job, name='clientdelete_job'),
    path('jobs/add/', views.addjob, name='addjobbyclient'),
    path('publish/<int:pk>/', views.publishjob, name='publishjob'),

    # Client Reports query
    path('clientreports/', views.clientapprovedreports, name='clientreports'),
    path('fetch_clientreportdata/', views.fetch_clientreportdata,
         name='fetch_clientreportdata'),

    # ----CLIENT SECTION------
    path('importclientjobs/', ClientImportView.as_view(), name='importclientjobs'),

    



]
