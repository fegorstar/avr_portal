from django import forms
from staffs.models import Client, Agent, Job, Report
from django.forms import FileField, Form
import os
from agents.validators import allow_only_images_validator, allow_only_imagesandfiles_validator
from accounts.models import User, UserProfile


class AgentForm(forms.ModelForm):
    proofOfId = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_imagesandfiles_validator])

    class Meta:
        model = Agent
        fields = ['address', 'fullname', 'proofOfId', 'guarantorName',
                  'BankAccountDetails', 'guarantorPhoneNumber']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class AgentuserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone_number']

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
        fields = ['buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                  'NameofindividualInterviewed', 'RelationshipWithCustomer', 'VerificationMessage', 'MoreComment', 'Landmark', 'photo1', 'photo2']
