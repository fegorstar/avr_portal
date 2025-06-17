from rest_framework import serializers
from staffs.models import  Job, Report, Client


class JobSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), required=True)
    clientJobrefID = serializers.CharField(required=True, allow_blank=False)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)
    address = serializers.CharField(required=True, allow_blank=False)
    
    class Meta:
        model = Job
        fields = ['clientJobrefID', 'ref_no', 'first_name', 'last_name', 'state', 'city',
                  'phone_number', 'email', 'address', 'client', 'published']

    


class ReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = Report

        fields = ['clientJobrefID','JobRefNo', 'buildingCondition', 'buildingColor', 'buildingType', 'CustomerRelationshipWithaddress', 'AddressResidential',
                  'NameofindividualInterviewed', 'RelationshipWithCustomer', 'VerificationMessage', 'MoreComment', 'Landmark', 'photo1', 'photo2', 'TAT', 'Reportstatus']

        
        