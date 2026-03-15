from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'reports'

urlpatterns = [
    # Public
    path('',                 view=views.index,             name='index'),
    path('report/<int:pk>/', view=views.report_detail,     name='report_detail'),
    path('annual/',          view=views.annual_report,     name='annual_report'),
    path('annual/pdf/',      view=views.annual_report_pdf, name='annual_report_pdf'),

    # Auth
    path('login/',    view=views.login_view,    name='login'),
    path('logout/',   view=views.logout_view,   name='logout'),
    path('register/', view=views.register_view, name='register'),

    # Profile & report management
    path('profile/',                      view=views.profile,        name='profile'),
    path('profile/download/',             view=views.my_reports_pdf, name='my_reports_pdf'),
    path('profile/create/',               view=views.create_report,  name='create_report'),
    path('profile/report/<int:pk>/edit/', view=views.edit_report,    name='edit_report'),
    path('report/<int:pk>/delete/',       view=views.delete_report,  name='delete_report'),
    path('profile/account/',              view=views.account,        name='account'),
    path('user/<str:username>/',          view=views.user_profile,   name='user_profile'),

    # Admin dashboard
    path('admin-panel/',                              view=views.admin_dashboard,           name='admin_dashboard'),
    path('admin-panel/account/<int:user_id>/',        view=views.admin_account_action,      name='admin_account_action'),
    path('admin-panel/accounts/approve-all/',         view=views.admin_approve_all_accounts,name='admin_approve_all_accounts'),
    path('admin-panel/report/<int:pk>/',              view=views.admin_report_action,       name='admin_report_action'),
    path('admin-panel/reports/approve-all/',          view=views.admin_approve_all_reports, name='admin_approve_all_reports'),
    path('admin-panel/academic-pdf/',                 view=views.admin_academic_pdf,        name='admin_academic_pdf'),

    # Password reset
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='reports/password_reset.html',
             email_template_name='reports/password_reset_email.html',
             success_url='/reports/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='reports/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='reports/password_reset_confirm.html',
             success_url='/reports/password-reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='reports/password_reset_complete.html'),
         name='password_reset_complete'),
]
