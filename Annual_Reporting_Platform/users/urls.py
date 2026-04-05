from django.urls import path
from .views import loginPage,logout_view,profile_view,create_report_view,delete_report

app_name= 'users'
urlpatterns = [
    path('login/',view=loginPage, name='login'),
    path('logout/', view=logout_view,name="logout"),
    path('profile/',view=profile_view,name="profile"),
    path("profile/create-report",view=create_report_view,name="create-report"),
    path("delete-report/<int:pk>",view=delete_report,name="delete-report"),
    # path('report/<int:pk>',view=reportView,name="report_detail"),
]