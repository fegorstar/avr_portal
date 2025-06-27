from django.db import models
from accounts.models import User, UserProfile
from django.db.models.fields.related import ForeignKey, OneToOneField
from shortuuid.django_fields import ShortUUIDField


class Client(models.Model):
    id = ShortUUIDField(
        length=10,
        max_length=40,
        prefix="OOLPC_",
        alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+!~-*", primary_key=True

    )
    user = models.OneToOneField(
        User, related_name='user', on_delete=models.CASCADE, blank=True, null=True)
    user_profile = models.OneToOneField(
        UserProfile, related_name='userprofile', on_delete=models.CASCADE, blank=True, null=True)
    client_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    tat_limit = models.CharField(max_length=50)
    unit_rate_within_tat = models.CharField(max_length=50)
    unit_rate_outside_tat = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.client_name


class Agent(models.Model):
    user = models.OneToOneField(
        User, related_name='agentuser', on_delete=models.CASCADE)
    user_profile = models.OneToOneField(
        UserProfile, related_name='agentuserprofile', on_delete=models.CASCADE)

    fullname = models.CharField(max_length=250, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    proofOfId = models.ImageField(
        upload_to='photos/proofOfID', blank=True, null=True,  default="")
    guarantorName = models.CharField(max_length=250, blank=True, null=True)
    BankAccountDetails = models.TextField(
        max_length=250, blank=True, null=True)
    guarantorPhoneNumber = models.CharField(
        max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        # solves the issue with nontype
        return self.fullname or ''


# Model to add Jobs (Jobs Table)
class Job(models.Model):

    # jobstatus- value and key
    jobstatus_choices = (
        ('0', 'Undone'),
        ('1', 'Done'),
        ('2', 'Rejected'),
    )

    # jobstatus- value and key
    published_choices = (
        ('0', 'No'),
        ('1', 'Yes'),
    )
# in django we dont need to define the primary key it happens automatically behind the scene
    ref_no = ShortUUIDField(
        length=10,
        max_length=40,
        prefix="OOLP_",
        alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+!~-*", unique=True

    )

    clientJobrefID = models.CharField(
        max_length=250,  blank=True, null=True, default="")
    first_name = models.CharField(max_length=250, null=True)
    last_name = models.CharField(
        max_length=250, blank=True, null=True, default="")
    phone_number = models.CharField(max_length=100, blank=True, default="")
    email = models.CharField(max_length=100, blank=True, default="")
    address = models.TextField(blank=True, null=True, default="")
    state = models.CharField(max_length=250, null=True, blank=True)
    city = models.CharField(max_length=250, null=True, blank=True)

    # using foreign key to join both both so as to fetch agents and clients to choose.
    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name='agents', blank=True, null=True, limit_choices_to={'is_active': True})
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='clients',  default="", limit_choices_to={'is_active': True})  # limit choice so as to know client active

    status = models.CharField(
        choices=jobstatus_choices, max_length=100, default="0")

    published = models.CharField(
        choices=published_choices, max_length=100, default="1", blank=True, null=True)

    # TAT = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    whenAssigned = models.DateTimeField(max_length=50, blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, null=True)
    assignedBy = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, related_name='assigned_by', null=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, related_name='updated_by', null=True)  # whoupdatedlast

    BATCH_NO = models.CharField(
        max_length=250, blank=True, default="")
    created_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    # to prevent users from saving duplicate records (in our case -jobs)
    class Meta:
        unique_together = ["clientJobrefID"]

    def __str__(self):
        return self.email


class Report(models.Model):

    # jobstatus- value and key
    reportstatus_choices = (
        ('0', 'Pending'),
        ('1', 'Approved'),
        ('2', 'Rejected'),
    )

    # jobstatus- value and key
    addressexist_choices = (
        ('Yes', 'Yes'),
        ('No', 'No'),
    )

    resides_choices = (
        ('Yes', 'Yes'),
        ('No', 'No'),
    )

    buildingCondition_choices = (
        ('Uncompleted', 'Uncompleted'),
        ('Completed', 'Completed'),
        ('N/A', 'N/A'),

    )

    buildingType_choices = (
        ('Bungalow', 'Bungalow'),
        ('Storey Building', 'Storey Building'),
        ('Duplex', 'Duplex'),
        ('Block of flat', 'Block of flat'),
        ('BQ', 'BQ'),
        ('Multiple Floors', 'Multiple Floors'),
        ('Terrace', 'Terrace'),
        ('N/A', 'N/A'),

    )

    CustomerRelationshipWithaddress_choices = (
        ('Landlord', 'Landlord'),
        ('Tenant', 'Tenant'),
        ('None', 'None'),
        ('N/A', 'N/A'),

    )

    AddressResidential_choices = (
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('N/A', 'N/A'),

    )

    VerificationMessage_choices = (
        ('Incomplete Information', 'Incomplete Information'),
        ('No Response at the Address', 'No Response at the Address'),
        ('Address Does Not Exist', 'Address Does Not Exist'),
        ('Security Agents prevented access to Address',
         'Security Agents prevented access to Address'),
        ('Address is an empty plot of Land', 'Address is an empty plot of Land'),
        ('The Customer has relocated', 'The Customer has relocated'),
        ('The Customer is not known at the address',
         'The Customer is not known at the address'),
        ('The Customer is known but does not reside in the premises',
         'The Customer is known but does not reside in the premises'),
        ('Address exists and customer is known',
         'Address exists and customer is known'),
        ('Customer does not live at the address but visits often',
         'Customer does not live at the address but visits often'),
        ('The Customer is deceased', 'The Customer is deceased'),
        ('The Customer works at the address but does not reside there',
         'The Customer works at the address but does not reside there'),
        ('Customer was met at a different house number',
         'Customer was met at a different house number'),
        ('Address is customers family house and does not reside there',
         'Address is customers family house and does not reside there'),
        ('Company is not known at the address',
         'Company is not known at the address'),
        ('Company is known and operate from the address',
         'Company is known and operate from the address'),
        ('Could not locate address',
         'Could not locate address'),
        ('Incomplete address',
         'Incomplete address'),



    )

    customer = models.ForeignKey(
        Job, on_delete=models.CASCADE, to_field="ref_no", related_name='customer', default="")  # must be entered

    JobRefNo = models.CharField(
        max_length=250, blank=True, null=True)

    clientJobrefID = models.CharField(
        max_length=250,  blank=True, null=True, default="")

    customerName = models.CharField(
        max_length=250, blank=True, null=True, default="")

    Client = models.CharField(
        max_length=250, blank=True, null=True)

    VerificationMessage = models.CharField(
        choices=VerificationMessage_choices, max_length=250)

    agent = models.CharField(
        max_length=250)  # required entry

    # so report can be searched by agent
    address = models.TextField(blank=True, null=True)

    Reportstatus = models.CharField(
        choices=reportstatus_choices, max_length=250, blank=True, null=True, default="0")  # made default value - so they won't have to always enter it in import

    buildingCondition = models.CharField(
        choices=buildingCondition_choices, max_length=250, blank=True, null=True)
    buildingColor = models.CharField(
        max_length=250,  default="", blank=True, null=True)
    buildingType = models.CharField(
        choices=buildingType_choices, max_length=250, default="", blank=True, null=True)
    CustomerRelationshipWithaddress = models.CharField(
        choices=CustomerRelationshipWithaddress_choices, max_length=250, blank=True, null=True)
    AddressResidential = models.CharField(
        choices=AddressResidential_choices, max_length=250, default="", blank=True, null=True)

    NameofindividualInterviewed = models.CharField(
        max_length=250, blank=True, null=True,  default="")
    RelationshipWithCustomer = models.CharField(
        max_length=250, blank=True, null=True,  default="")

    MoreComment = models.TextField(
        max_length=250, blank=True, null=True,  default="")
    Landmark = models.CharField(
        max_length=250, blank=True, null=True,  default="")
    photo1 = models.ImageField(
        upload_to='photos/address_pictures', blank=True, null=True,  default="")
    photo2 = models.ImageField(
        upload_to='photos/address_pictures', blank=True, null=True, default="")
    TAT = models.CharField(
        max_length=250, blank=True, null=True)  # toget the TAT
    approvedBy = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, related_name='approved_by', null=True)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    saved = models.BooleanField(default=False,help_text="Flag indicating this report was partially saved (lat/long only)")
    
    
    created_at = models.DateTimeField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True, editable=True)

    # to prevent users from saving duplicate records (in our case -reports)

    class Meta:
        unique_together = ["customer"]

    def __str__(self):
        return self.MoreComment

    # this code will remove previous images and replace it with a new if updated.
    def save(self, *args, **kwargs):
        try:
            this = Report.objects.get(id=self.id)
            if this.photo1 != self.photo1:
                this.photo1.delete()
            elif this.photo2 != self.photo2:
                this.photo2.delete()
        except:
            pass
        super(Report, self).save(*args, **kwargs)
