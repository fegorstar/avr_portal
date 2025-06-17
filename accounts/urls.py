from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),

    path('myAccount/', views.myAccount, name='myAccount'),
    path('staffDashboard/', views.staffDashboard, name='staffDashboard'),
    path('agentDashboard/', views.agentDashboard, name='agentDashboard'),
    path('clientDashboard/', views.clientDashboard, name='clientDashboard'),

    #Staff section
    path('staff/', include('staffs.urls')),

    #Agent section
    path('agent/', include('agents.urls')),

    #Client section
    path('client/', include('clients.urls')),

]
