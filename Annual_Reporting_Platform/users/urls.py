from django.urls import path
from .views import loginPage

app_name= 'users'
urlpatterns = [
    path('login/',view=loginPage, name='login'),
    # path('report/<int:pk>',view=reportView,name="report_detail"),
]