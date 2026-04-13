from django.urls import path
from .views import (
    adminReportView,
    adminAccountView,
    generateReportsView,
    csvPreviewReportsView,
    generateStaffCSVView,
    csvPreviewStaffView,
)


app_name = 'administration'
urlpatterns = [
    path('admin-reports/', adminReportView, name='admin-reports'),
    path('admin-accounts/', adminAccountView, name='admin-accounts'),
    path('generate-reports/', generateReportsView, name='generate-reports'),
    path('csv-preview/reports/', csvPreviewReportsView, name='csv-preview-reports'),
    path('csv-upload/staff/', generateStaffCSVView, name='csv-upload-staff'),
    path('csv-preview/staff/', csvPreviewStaffView, name='csv-preview-staff'),
]