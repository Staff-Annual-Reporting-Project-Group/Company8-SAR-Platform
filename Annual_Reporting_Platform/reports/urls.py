from django.urls import path
from .views import annual_report, index,reportView,deleteReport,annual_report_pdf,my_reports_pdf

app_name= 'reports'
urlpatterns = [
    path('',view=index, name='index'),
    path('report/<int:pk>',view=reportView,name="report_detail"),
    path('report/delete/<int:pk>',view=deleteReport,name="delete_report"),
    path('annual-report/',view=annual_report,name="annual_report"),
     path('annual/pdf/', view=annual_report_pdf, name='annual_report_pdf'),
     path('my-reports/pdf/', view=my_reports_pdf, name='my_reports_pdf'),

]
