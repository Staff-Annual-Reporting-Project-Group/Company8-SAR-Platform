from django.urls import path
from .views import index

app_name= 'reports'
urlpatterns = [
    path('',view=index, name='index'),
]
