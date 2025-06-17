from import_export import resources
from .models import Job, Client, Agent, User, UserProfile, Report
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

# bulk admin import/export resource for Job


class JobResource(resources.ModelResource):

    client = Field(
        column_name='client',
        attribute='client',
        widget=ForeignKeyWidget(model=Client, field='client_name'))  # relating to the Client field-mapping

    agent = Field(
        column_name='agent',
        attribute='agent',
        widget=ForeignKeyWidget(model=Agent, field='fullname'))  # relating to the Agent field-mapping

    class Meta:
        model = Job



# # bulk admin import/export resource for Agent
# class AgentResource(resources.ModelResource):

#     user = Field(
#         column_name='user',
#         attribute='user',
#         widget=ForeignKeyWidget(model=User, field='id'))  # relating to the Agent field-mapping

#     class Meta:
#         model = Agent


# bulk admin import/export resource for Report
class ReportResource(resources.ModelResource):

    customer = Field(
        column_name='customer',
        attribute='customer',
        widget=ForeignKeyWidget(model=Job, field='ref_no'))  # relating to the Job whhere ref_no is the PK field-mapping
    Client = Field(
        column_name='Client',
        attribute='Client',
        widget=ForeignKeyWidget(model=Client, field='client_name'))  # relating to the Client field-mapping

    class Meta:
        model = Report
