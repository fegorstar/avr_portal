# jobs/filters.py
import django_filters
from .models import Job, Report, Client, Agent
from django import forms

from django_filters import DateFromToRangeFilter


class DateRangeWidget(django_filters.widgets.RangeWidget):
    def __init__(self, attrs=None):
        widgets = (forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                   forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
        super().__init__(attrs=attrs)  # Remove widgets argument


class JobFilter(django_filters.FilterSet):

    address = django_filters.CharFilter(
        field_name='address', lookup_expr='icontains')
    first_name = django_filters.CharFilter(
        field_name='first_name', lookup_expr='icontains')
    last_name = django_filters.CharFilter(
        field_name='last_name', lookup_expr='icontains')
    state = django_filters.CharFilter(
        field_name='state', lookup_expr='icontains')
    city = django_filters.CharFilter(
        field_name='city', lookup_expr='icontains')
    clientJobrefID = django_filters.CharFilter(
        field_name='clientJobrefID', lookup_expr='icontains')
    client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.all(),
        field_name='client__client_name',
        to_field_name='client_name',
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )

    agent = django_filters.ModelChoiceFilter(
        queryset=Agent.objects.all(),  # Replace with your actual Agent model queryset
        field_name='agent__fullname',
        to_field_name='fullname',
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )

    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=Job.jobstatus_choices,
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )
    ref_no = django_filters.CharFilter(
        field_name='ref_no', lookup_expr='icontains')

    created_at = django_filters.DateFromToRangeFilter(
        field_name='created_at', label='Date Range', widget=DateRangeWidget(attrs={'class': 'form-control'}))

    class Meta:
        model = Job
        fields = ['clientJobrefID', 'first_name', 'last_name', 'ref_no',
                  'agent', 'status', 'client', 'BATCH_NO', 'state', 'city', 'address', 'created_at']


class ReportFilter(django_filters.FilterSet):

    JobRefNo = django_filters.CharFilter(
        field_name='JobRefNo', lookup_expr='icontains')

    clientJobrefID = django_filters.CharFilter(
        field_name='clientJobrefID', lookup_expr='icontains')

    created_at = django_filters.DateTimeFilter(
        field_name='created_at', lookup_expr='icontains')

    Client = django_filters.ModelChoiceFilter(
        queryset=Client.objects.all(),
        field_name='Client',
        to_field_name='client_name',
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )

    address = django_filters.CharFilter(
        field_name='address', lookup_expr='icontains')

    agent = django_filters.ModelChoiceFilter(
        queryset=Agent.objects.all(),
        field_name='agent',
        to_field_name='fullname',
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )

    Reportstatus = django_filters.ChoiceFilter(
        field_name='Reportstatus',
        choices=Report.reportstatus_choices,
        widget=forms.Select(attrs={'class': 'form-control form-select'}),
    )

    created_at = django_filters.DateFromToRangeFilter(
        field_name='created_at', label='Date Range', widget=DateRangeWidget(attrs={'class': 'form-control'}))

    class Meta:
        model = Report
        fields = ['clientJobrefID', 'JobRefNo', 'Reportstatus',
                  'created_at', 'Client', 'agent', 'address']
