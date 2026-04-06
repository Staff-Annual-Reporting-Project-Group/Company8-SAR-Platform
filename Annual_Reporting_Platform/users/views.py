from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from reports.models import Report,Category,Committee,Participant
from django.db import transaction
from .extra_functionality import verify_title,verify_description
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)# Create a logger for this module the__name__ variable will be set to the name of the module, which is a common practice for organizing loggers in Python applications.
# Create your views here.
def loginPage(request):
    if request.user.is_authenticated:
        redirect('reports:index')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        #print("Tried with " + username)
        user = User.objects.filter(Q(username=username) | Q(email = username)).first()
        if not user:
            messages.error(request,"User does not exist")
            return redirect('users:login')
        username = user.username
        user = authenticate(request, username =username, password=password)
        if user is not None:
            login(request,user)
            return redirect('reports:index')
        else:
            messages.error(request, 'Username OR password does not exist')

    return render(request,'users/login.html',{})


def logout_view(request):
    logout(request)
    return redirect('reports:index')

@login_required
def profile_view(request):
    q = request.GET.get('q', '').strip()
    period = request.GET.get('period', '').strip()
    report_type = request.GET.get('report_type', '').strip()

    reports = Report.objects.user_reports(request.user)

    if q:
        reports = reports.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    if period or report_type:
        reports = reports.filterReports(
            period=period,
            report_type=report_type,
            committee=None,
            participant=None
        )

    context = {
        'reports': reports,
        'q': q,
        'period': period,
        'report_type': report_type,
        'page': 'reports',
    }
    return render(request, 'users/profile.html', context)

@login_required
def delete_report(request, pk):
    report = get_object_or_404(Report, id=pk, user=request.user)

    if request.method == 'POST':
        try:
            report.delete()
            messages.success(request, 'Report deleted successfully.')
        except Exception:
            messages.error(request, 'Unable to delete report.')
        return redirect('users:profile')

    return redirect('users:profile')




@login_required
def create_report_view(request):
    categories = Category.objects.all().order_by('name')
    committees = Committee.objects.all().order_by('name')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category', '').strip()
        committee_ids = request.POST.getlist('committees')
        participant_string = request.POST.get('participants', '').strip()
        feature_image = request.FILES.get('image')

        errors = []

        if not title:
            errors.append("Title is required.")

        else:
            if not verify_title(title):
                errors.append("Title must be at least 5 characters long and cannot contain profanity.")

        if not description:
            errors.append("Description is required.")
            if not verify_description(description):
                errors.append("Description must be at least 10 characters long and cannot contain profanity.")

        if not category_id:
            errors.append("Category is required.")

        category = None
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                errors.append("Selected category is invalid.")

        selected_committees = Committee.objects.filter(id__in=committee_ids)

        # Parse participants from hidden comma-separated field
        raw_names = participant_string.split(',')
        for name in raw_names:
            cleaned_name = name.strip()
            if cleaned_name and not verify_title(cleaned_name):
                errors.append(f"Participant name '{cleaned_name}' must be at least 5 characters long and cannot contain profanity.")
        participant_names = []
        seen = set()

        for name in raw_names:
            cleaned_name = name.strip()
            if cleaned_name:
                key = cleaned_name.lower()
                if key not in seen:
                    seen.add(key)
                    participant_names.append(cleaned_name)

        if errors:
            for error in errors:
                messages.error(request, error)

            context = {
                'page': 'create-report',
                'categories': categories,
                'committees': committees,
                'form_data': {
                    'title': title,
                    'description': description,
                    'category_id': category_id,
                    'committee_ids': committee_ids,
                    'participants': participant_string,
                }
            }
            return render(request, "users/create_report.html", context)

        try:
            with transaction.atomic():#Joshua Weekes here this part is very important to ensure that the A part of the ACID properties are maintained
                report = Report.objects.create(
                    user=request.user,
                    title=title,
                    description=description,
                    category=category,
                    feature_image=feature_image if feature_image else 'default_image.jpg',
                )

                if selected_committees.exists():
                    report.committees.set(selected_committees)

                participant_objects = []
                for full_name in participant_names:
                    participant = Participant.objects.filter(name__iexact=full_name).first()
                    if not participant:
                        participant = Participant.objects.create(name=full_name)
                    participant_objects.append(participant)

                if participant_objects:
                    report.participants.set(participant_objects)
            logger.info(f"Report '{report.title}' created successfully by user '{request.user.username}' with id {report.id}")
            messages.success(request, "Report created successfully.")
            cache.clear()# Clear the cache to ensure that the new report appears in the listings immediately
            return redirect('users:profile')

        except Exception:
            logger.error(f"Error occurred while creating report by user '{request.user.username}': {str(e)}")
            messages.error(request, "An error occurred while creating the report.")

            context = {
                'page': 'create-report',
                'categories': categories,
                'committees': committees,
                'form_data': {
                    'title': title,
                    'description': description,
                    'category_id': category_id,
                    'committee_ids': committee_ids,
                    'participants': participant_string,
                }
            }
            return render(request, "users/create_report.html", context)

    context = {
        'page': 'create-report',
        'categories': categories,
        'committees': committees,
    }
    return render(request, "users/create_report.html", context)