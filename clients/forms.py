from django import forms
from staffs.models import Client, Agent, Job, Report
from django.forms import FileField, Form
import os
from agents.validators import allow_only_images_validator
from accounts.models import User, UserProfile


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['client_name', 'tat_limit', 'address',
                  'unit_rate_within_tat', 'unit_rate_outside_tat']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class ClientuserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class clientJobForm(forms.ModelForm):
    def __init__(self, request=None, user=None, *args, **kwargs):
        super(clientJobForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['client'].queryset = Client.objects.filter(
                user=user)
            self.fields['client'].empty_label = None

    class Meta:
        model = Job
        fields = ['clientJobrefID', 'first_name', 'last_name', 'state', 'city',
                  'phone_number', 'email', 'address', 'client', 'agent', 'BATCH_NO', 'published']


class PublishJobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['published']

    # To make the form show the given style of our template
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
            visible.field.widget.attrs['id'] = 'selectedagent'


# i used django-wddget-weaks to tweak how each input will be
class ClientEditJobForm(forms.ModelForm):
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
