from django.urls import path
from .views import adminReportView, adminAccountView


app_name= 'administration'
urlpatterns = [
   path('admin-reports/', adminReportView, name='admin-reports'),
   path('admin-accounts/', adminAccountView, name='admin-accounts'),

]