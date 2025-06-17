from django.urls import path, include
from . import views
from agents.views import UploadReportViewbyagent

urlpatterns = [
    path('agentprofile/', views.agentprofile, name='agentprofile'),
    # ==================Jobs========================
    path('agentassignedjobs/', views.agentassignedjobs, name='agentassignedjobs'),
    path('fetch_agentunassignedjobs/', views.fetch_agentunassignedjobs,
         name='fetch_agentunassignedjobs'),
    path('fetch_job_detailsagentsection/', views.fetch_job_detailsagentsection,
         name='fetch_job_detailsagentsection'),  # This view fetches product details
    path('reportAddress/<int:pk>/', views.Address_Report, name='reportAddress'),
    path('reject-job/<int:job_id>/', views.reject_job, name='reject-job'),



    # ===========================reports===============================

    path('myreport/', views.agentreport, name='myreport'),
    path('fetchagentreportdata/', views.fetchagentreportdata,
         name='fetchagentreportdata'),
    path('fetchagentreportdetails/', views.fetchagentreportdetails,
         name='fetchagentreportdetails'),  # This view fetches report details
    path('editagentreport/<int:pk>/', views.EditReport, name='editagentreport'),
    path('agentrejectedreports/', views.agentrejectedreports,
         name='agentrejectedreports'),
    path('fetch_agentrejectedreportdata/', views.fetch_agentrejectedreportdata,
         name='fetch_agentrejectedreportdata'),
    path('EditagentRejectedReport/<int:pk>/',
         views.EditagentRejectedReport, name='EditagentRejectedReport'),
    path('uploadreportbyagent/',  UploadReportViewbyagent.as_view(),
         name='uploadreportbyagent'),


]
