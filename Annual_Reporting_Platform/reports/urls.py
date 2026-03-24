from django.urls import path
from .views import index,reportView,deleteReport

app_name= 'reports'
urlpatterns = [
    path('',view=index, name='index'),
    path('report/<int:pk>',view=reportView,name="report_detail"),
    path('report/delete/<int:pk>',view=deleteReport,name="delete_report"),
]
