from django.urls import path, include
from . import views

urlpatterns = [

# JOBS API URLS
path('jobs/<str:client_id>/', views.JobCreateView.as_view(), name='job-create'),
path('jobs/list/<str:client_id>/', views.JobListView.as_view(), name='job-list'),
# path('jobs/', views.AllJobsView.as_view(), name='all-jobs'),
path('jobs/status/<str:status_code>/', views.JobsByStatusView.as_view(), name='jobs-by-status'),

#REPORTS API URLS
# path('reports/', views.RetrieveAllReportsAPIView.as_view(), name='all-reports'),
path('reports/client/<str:client_id>/', views.ClientReportsView.as_view(), name='client-reports'),
path('reports/status/<str:status_code>/', views.ReportsByStatusView.as_view(), name='reports-by-status'),




]

