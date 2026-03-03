from django.urls import path
from .views import index,reportView

app_name= 'reports'
urlpatterns = [
    path('',view=index, name='index'),
    path('report/<int:pk>',view=reportView,name="report_detail"),
]
