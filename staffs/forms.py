from django import forms
from .models import Client, Agent, Job, Report
from django.forms import FileField, Form
import os
from agents.validators import allow_only_images_validator


class JobForm(forms.ModelForm):

    class Meta:
        model = Job
        fields = ['clientJobrefID', 'first_name', 'last_name', 'state', 'city',
                  'phone_number', 'email', 'address', 'client', 'agent', 'BATCH_NO', 'published']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

# i used django-wddget-weaks to tweak how each input will be


class uploadJobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['clientJobrefID', 'first_name', 'last_name', 'state', 'city',
                  'phone_number', 'email', 'address', 'client', 'BATCH_NO']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class AssignForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['agent', 'whenAssigned']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['id'] = 'selectedagent'


class UpdateReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['Reportstatus']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['id'] = 'selectedagent'

# i used django-wddget-weaks to tweak how each input will be


class EditJobForm(forms.ModelForm):
    class Meta:
        model = Job
        # define the fields you want to see
        fields = ['first_name', 'last_name', 'state', 'city',
                  'phone_number', 'email', 'address', 'BATCH_NO', 'status', 'published']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class ImportForm(Form):
    jobs_file = FileField(label='Select the Jobs Upload file:')
    # To make the form show the given style of our template

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['onchange'] = 'triggerValidation(this)'
            visible.field.widget.attrs['id'] = 'csvFileInput'
            visible.field.widget.attrs['accept'] = '.csv'


# report form
class ReportJobForm(forms.ModelForm):
    # we are using validator to validate the file upload
    photo1 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)  # i put required to false to make it optional
    # we are using validator to validate the file upload

    photo2 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)  # i put required to false to make it optional

    class Meta:
        model = Report
        fields = ['JobRefNo', 'TAT', 'buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                  'NameofindividualInterviewed', 'RelationshipWithCustomer', 'VerificationMessage', 'MoreComment', 'Landmark', 'photo1', 'photo2', 'agent', 'address']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


# editreport form
class EditReportForm(forms.ModelForm):
   # we are using validator to validate the file upload
    photo1 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)  # i put required to false to make it optional
    # we are using validator to validate the file upload

    photo2 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)  # i put required to false to make it optional

    class Meta:
        model = Report
        fields = ['Reportstatus', 'buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                  'NameofindividualInterviewed', 'RelationshipWithCustomer', 'VerificationMessage', 'MoreComment', 'Landmark', 'photo1', 'photo2']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class uploadReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['customer', 'TAT', 'VerificationMessage', 'buildingCondition', 'buildingColor',
                  'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential', 'NameofindividualInterviewed', 'RelationshipWithCustomer', 'MoreComment', 'Landmark']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class ImportReportForm(Form):
    report_file = FileField(label='Select the Report Upload file:')
    # To make the form show the given style of our template

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['onchange'] = 'triggerValidation(this)'
            visible.field.widget.attrs['id'] = 'csvFileInput'
            visible.field.widget.attrs['accept'] = '.csv'


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Upload CSV File')
