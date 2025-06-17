from django.contrib import admin
from staffs.models import Client, Agent, Job, Report
from import_export.admin import ImportExportModelAdmin
from .resources import JobResource, ReportResource
from rangefilter.filters import (
    DateRangeFilter,
    DateTimeRangeFilter,
)

class ClientAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'client_name', 'user', 'created_at')
    list_display_links = ('id', 'user', 'client_name')
    search_fields = ['id', 'client_name', 'user', 'created_at']

class AgentAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'fullname', 'proofOfId', 'guarantorName',
                    'guarantorPhoneNumber', 'address', 'created_at')
    list_display_links = ('id', 'fullname')
    search_fields = ['id', 'fullname', 'address', 'created_at']
    # resource_class = AgentResource

# Show jobs
class JobAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_filter = (
        'agent',
        'status',
        'client',
        ('created_at', DateRangeFilter),
        ('modified_at', DateTimeRangeFilter),
    )
    list_display = ('ref_no', 'clientJobrefID', 'first_name',
                    'last_name', 'client', 'agent', 'address', 'status', 'created_at')
    list_display_links = ('ref_no', 'first_name')
    search_fields = ['ref_no', 'clientJobrefID', 'first_name',
                     'last_name', 'address', 'created_at']
    resource_class = JobResource

# Show reports
class JobReportAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_filter = (
        'agent',
        'Client',
        'Reportstatus',
        ('created_at', DateRangeFilter),
        ('modified_at', DateTimeRangeFilter),
    )
    list_display = ('customer_id', 'customerName', 'address', 'VerificationMessage', 'agent',
                    'Reportstatus', 'created_at')
    list_display_links = ('customer_id',)
    search_fields = ['clientJobrefID', 'JobRefNo', 'Reportstatus',
                     'agent', 'address', 'created_at', 'Client']
    resource_class = ReportResource

admin.site.register(Client, ClientAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(Report, JobReportAdmin)