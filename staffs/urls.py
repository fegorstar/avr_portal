from django.urls import path
from . import views
from accounts import views as AccountViews
from django.views.decorators.csrf import csrf_exempt
from staffs.views import (
    PendingBulkReportApprovalView, 
    RejectedBulkReportApprovalView, 
    allreportbulk_approvalView, 
    ImportView, 
    AssignBulkJobView, 
    UploadReportViewbystaff
)
from .views import ApprovalAndSendTemplateView

urlpatterns = [

    # ================== Dashboard and Profile =========================
    path('', AccountViews.staffDashboard, name='staff'),
    path('staffprofile/', views.staffprofile, name='staffprofile'),

    # ============================== ALL JOBS SECTION =========================
    path('jobs/', views.jobs, name='jobs'),
    path('fetch_data/', views.fetch_data, name='fetch_data'),
    path('fetch_job_details/', views.fetch_job_details, name='fetch_job_details'),
    path('edit_job_details/', views.edit_job_details, name='edit_job_details'),
    path('update_job/', views.update_job, name='update_job'),
    path('delete_job/', views.delete_job, name='delete_job'),
    path('assignbulkjobs/', AssignBulkJobView.as_view(), name='assignbulkjobs'),
    path('rejectedjobs/', views.rejectedjobs, name='rejectedjobs'),
    path('fetchrejected_job/', views.fetchrejected_job, name='fetchrejected_job'),
    # ============================== END ALL JOBS SECTION =========================

    # ======================== AGENTS PENDING JOBS =========================
    path('agentpendingjobs/', views.agentpendingjobs, name='agentpendingjobs'),
    path('fetch_allagentspendingjobs/', views.fetch_allagentspendingjobs, name='fetch_allagentspendingjobs'),
    path('agentDetails/', views.agentDetails, name='agentDetails'),
    path('fetch_allagentDetails/', views.fetch_agent_details, name='fetch_allagentDetails'),
    path('fetch_agent_details/', views.fetchagentDetailsModal, name='fetch_agent_details'),
    path('agentjobs/<int:agent_id>/jobs/', views.agent_jobs, name='agentjobs'),
    # ======================== END AGENTS PENDING JOBS =========================

    # ============================= UNASSIGNED JOBS SECTION =========================
    path('unassignedjobs/', views.unassignedjobs, name='unassignedjobs'),
    path('fetch_unassigneddata/', views.fetch_unassigneddata, name='fetch_unassigneddata'),
    path('jobs/add/', views.addjob, name='addjobbystaff'),
    path('import/', ImportView.as_view(), name='uploadjob'),  # upload bulk jobs
    # ============================= END UNASSIGNED JOBS SECTION =========================

    # ============================ REPORT SECTION =========================
    path('uploadreports/', UploadReportViewbystaff.as_view(), name='uploadreports'),
    path('allreports/', views.allreports, name='allreports'),
    path('fetch_allreportdata/', views.fetch_allreportdata, name='fetch_allreportdata'),
    
    #FOR REPORT UPDATE
    path('fetch-report-details-staff/<int:report_id>/', views.fetch_report_details_staff, name='fetch-report-details-staff'),
    path('update_reportdetails_staff/<int:report_id>/', views.update_reportdetails_staff, name='update_reportdetails_staff'),
    
    

    path('allreportbulk_approval/', allreportbulk_approvalView.as_view(), name='allreportbulk_approval'),
    path('reportinPdf/<int:pk>/', views.reportinPdf, name='reportinPdf'),
    path('pendingreports/', views.Pendingreports, name='pendingreports'),
    path('fetch_pendingreportdata/', views.fetch_pendingreportdata, name='fetch_pendingreportdata'),
    path('fetch_report_details/', views.fetch_report_details, name='fetch_report_details'),
    path('Pendingbulk_report_approval/', PendingBulkReportApprovalView.as_view(), name='Pendingbulk_report_approval'),
    path('rejectedreports/', views.rejectedreports, name='rejectedreports'),
    path('fetch_rejectedreportdata/', views.fetch_rejectedreportdata, name='fetch_rejectedreportdata'),
    path('RejectedBulkReportApproval/', RejectedBulkReportApprovalView.as_view(), name='RejectedBulkReportApproval'),
    path('delete_report/<int:report_id>/', views.delete_report, name='delete_report'),
    path('approvedreports/', views.Approvedreports, name='approvedreports'),
    path('fetch_approvedreportdata/', views.fetch_approvedreportdata, name='fetch_approvedreportdata'),
    path('UrgentReports/', views.searchbyaddress, name='UrgentReports'),
    path('OutstandingReports/', views.OutstandingReport, name='OutstandingReports'),
    path('NotFoundjobs/', views.ConfirmJobnotsent, name='NotFoundjobs'),
    path('search-reports/', views.search_reports, name='search_reports'),
    path('approve-and-send/', ApprovalAndSendTemplateView.as_view(), name='approve_and_send'),
    path('allsavedreports/', views.Savedreports, name='allsavedreports'),
    path('fetchallsavedreportdata/', views.fetch_savedreportdata, name='fetchallsavedreportdata'),
    # ============================ END REPORT SECTION =========================

    # ============================ STATISTICS =========================
    path('job-statistics/', views.JobStatisticsView, name='job-statistics'),
    path('report-statistics/', views.ReportStatisticsView, name='report_statistics'),
    # ============================ END STATISTICS =========================

]
