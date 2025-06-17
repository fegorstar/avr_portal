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
    # Adding fields for latitude, longitude, and formatted address
    latitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = forms.DecimalField(max_digits=9, decimal_places=6, required=False)
 
    # File upload fields with validation
    photo1 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)
    photo2 = forms.FileField(widget=forms.FileInput(
        attrs={'class': 'btn btn-info'}), validators=[allow_only_images_validator], required=False)

    class Meta:
        model = Report
        fields = ['buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 
                  'AddressResidential', 'NameofindividualInterviewed', 'RelationshipWithCustomer', 
                  'VerificationMessage', 'MoreComment', 'Landmark', 'photo1', 'photo2', 'latitude', 'longitude']