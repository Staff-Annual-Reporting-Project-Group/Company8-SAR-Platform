from django.urls import path
from .views import account_view, loginPage,logout_view,profile_view,create_report_view,delete_report,edit_report_view,registerView  



app_name= 'users'
urlpatterns = [
    path('login/',view=loginPage, name='login'),
    path('logout/', view=logout_view,name="logout"),
    path('profile/',view=profile_view,name="profile"),
    path("profile/create-report",view=create_report_view,name="create-report"),
    path("profile/edit-report/<int:pk>",view=edit_report_view,name="edit-report"),
    path("delete-report/<int:pk>",view=delete_report,name="delete-report"),
    path("account/", view=account_view, name="account"),
    path("register/",view=registerView, name="register")

]