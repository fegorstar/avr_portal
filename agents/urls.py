from django.urls import path
from . import views
from agents.views import UploadReportViewbyagent

urlpatterns = [

    # ================== Agent Profile =========================
    path('agentprofile/', views.agentprofile, name='agentprofile'),


    # ================== Jobs =========================
    path('agentassignedjobs/', views.agentassignedjobs, name='agentassignedjobs'),
    path('fetch_agentunassignedjobs/', views.fetch_agentunassignedjobs, name='fetch_agentunassignedjobs'),
    path('fetch_job_detailsagentsection/', views.fetch_job_detailsagentsection, name='fetch_job_detailsagentsection'),
    
    # Report Address
    path('reportAddress/<int:report_id>/', views.Address_Report, name='reportAddress'),
    
    # Partial Save Report
    path('partialSavereport/<int:report_id>/', views.partial_report_save, name='partialSavereport'),

    # Reject Job
    path('reject-job/<int:job_id>/', views.reject_job, name='reject-job'),


    # ================== Reports =========================
    path('myreport/', views.agentreport, name='myreport'),
    path('fetchagentreportdata/', views.fetchagentreportdata, name='fetchagentreportdata'),

    # Saved Reports
    path('savedreports/', views.agentsavedreports, name='savedreports'),
    path('fetchagentsavedreportdata/', views.fetchagentsavedreportdata, name='fetchagentsavedreportdata'),
    
    # Fetch Report Details for Editing
    path('fetch-agent-report-details/', views.fetchagentreportdetails, name='fetchagentreportdetails'),
    
    path('fetch-edit-report-details/<int:report_id>/', views.fetch_edit_report_details, name='fetch-edit-report-details'),
    # Update Report
    path('update-report/<int:report_id>/', views.update_report, name='update_report'),

    # Rejected Reports
    path('agentrejectedreports/', views.agentrejectedreports, name='agentrejectedreports'),
    path('fetch_agentrejectedreportdata/', views.fetch_agentrejectedreportdata, name='fetch_agentrejectedreportdata'),

    # ================== Report Upload =========================
    path('uploadreportbyagent/', UploadReportViewbyagent.as_view(), name='uploadreportbyagent'),
]
