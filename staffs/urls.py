from django.urls import path, include
from . import views
from accounts import views as AccountViews
from django.views.decorators.csrf import csrf_exempt
from staffs.views import PendingBulkReportApprovalView, RejectedBulkReportApprovalView, allreportbulk_approvalView, ImportView, AssignBulkJobView, UploadReportViewbystaff
from .views import ApprovalAndSendTemplateView

urlpatterns = [
    path('', AccountViews.staffDashboard, name='staff'),
    path('staffprofile/', views.staffprofile, name='staffprofile'),

    # ==============================ALL JOBS SECTION URL=====================================
    path('jobs/', views.jobs, name='jobs'),
    # This view should return the data for the data table
    path('fetch_data/', views.fetch_data, name='fetch_data'),
    path('fetch_job_details/', views.fetch_job_details,
         name='fetch_job_details'),  # This view fetches product details
    path('edit_job_details/', views.edit_job_details, name='edit_job_details'),
    path('update_job/', views.update_job, name='update_job'),
    path('delete_job/', views.delete_job, name='delete_job'),
    path('assignbulkjobs/', AssignBulkJobView.as_view(), name='assignbulkjobs'),
    path('rejectedjobs/', views.rejectedjobs, name='rejectedjobs'),
    path('fetchrejected_job/', views.fetchrejected_job, name='fetchrejected_job'),
    # ==============================END ALL JOBS SECTION URL=====================================

    # =======================AGENTS PENDING JOBS URL------------------------------------------
    path('agentpendingjobs/', views.agentpendingjobs, name='agentpendingjobs'),

    path('fetch_allagentspendingjobs/', views.fetch_allagentspendingjobs,
         name='fetch_allagentspendingjobs'),

    path('agentDetails/', views.agentDetails,
         name='agentDetails'),
    path('fetch_allagentDetails/', views.fetch_agent_details,
         name='fetch_allagentDetails'),
    path('fetch_agent_details/', views.fetchagentDetailsModal,
         name='fetch_agent_details'),  # This view fetches agent details

    path('agentjobs/<int:agent_id>/jobs/', views.agent_jobs, name='agentjobs'),






    # =============================ALL- UNASSIGNED JOBS SECTION==========================
    path('unassignedjobs/', views.unassignedjobs, name='unassignedjobs'),
    path('fetch_unassigneddata/', views.fetch_unassigneddata,
         name='fetch_unassigneddata'),
    path('jobs/add/', views.addjob, name='addjobbystaff'),
    path('import/', ImportView.as_view(), name='uploadjob'),  # upload bulk jobs

    # =============================END OF ALL- UNASSIGNED JOBS SECTION==========================



    # ============================REPORT SECTION==================================================
    path('uploadreports/', UploadReportViewbystaff.as_view(), name='uploadreports'),
    path('allreports/', views.allreports, name='allreports'),
    path('fetch_allreportdata/', views.fetch_allreportdata,name='fetch_allreportdata'),
    path('editallreport/<int:pk>/',views.EditallReport, name='editallreport'),
    path('allreportbulk_approval/', allreportbulk_approvalView.as_view(),name='allreportbulk_approval'),
    path('reportinPdf/<int:pk>/', views.reportinPdf, name='reportinPdf'),
    path('pendingreports/', views.Pendingreports, name='pendingreports'),
    path('fetch_pendingreportdata/', views.fetch_pendingreportdata, name='fetch_pendingreportdata'),
    path('fetch_report_details/', views.fetch_report_details, name='fetch_report_details'),  # This view fetches report details
    path('editpendingreport/<int:pk>/',views.EditPendingReport, name='editpendingreport'),
    path('Pendingbulk_report_approval/', PendingBulkReportApprovalView.as_view(),name='Pendingbulk_report_approval'),
    path('rejectedreports/', views.rejectedreports, name='rejectedreports'),
    path('fetch_rejectedreportdata/', views.fetch_rejectedreportdata,
         name='fetch_rejectedreportdata'),
    path('EditRejectedReport/<int:pk>/',
         views.EditRejectedReport, name='EditRejectedReport'),
    path('RejectedBulkReportApproval/', RejectedBulkReportApprovalView.as_view(),
         name='RejectedBulkReportApproval'),
    path('delete_report/<int:report_id>/',
         views.delete_report, name='delete_report'),


    path('approvedreports/', views.Approvedreports, name='approvedreports'),
    path('fetch_approvedreportdata/', views.fetch_approvedreportdata,
         name='fetch_approvedreportdata'),


    path('UrgentReports/', views.searchbyaddress, name='UrgentReports'),
    path('OutstandingReports/', views.OutstandingReport, name='OutstandingReports'),
    path('NotFoundjobs/', views.ConfirmJobnotsent, name='NotFoundjobs'),
    path('search-reports/', views.search_reports, name='search_reports'),
    path('approve-and-send/', ApprovalAndSendTemplateView.as_view(),
         name='approve_and_send'),
    # statistics
    path('job-statistics/', views.JobStatisticsView,
         name='job-statistics'),
    path('report-statistics/', views.ReportStatisticsView,
         name='report_statistics'),


]
