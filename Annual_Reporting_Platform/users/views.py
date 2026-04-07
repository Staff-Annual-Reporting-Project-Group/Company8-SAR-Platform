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


def _get_report_form_dependencies():
    return {
        'categories': Category.objects.all().order_by('name'),
        'committees': Committee.objects.all().order_by('name'),
    }


def _get_report_form_data(request):
    return {
        'title': request.POST.get('title', '').strip(),
        'description': request.POST.get('description', '').strip(),
        'category_id': request.POST.get('category', '').strip(),
        'committee_ids': request.POST.getlist('committees'),
        'participants': request.POST.get('participants', '').strip(),
        'feature_image': request.FILES.get('image'),
    }


def _parse_participant_names(participant_string):
    raw_names = participant_string.split(',')
    participant_names = []
    seen = set()

    for name in raw_names:
        cleaned_name = name.strip()
        if cleaned_name:
            key = cleaned_name.lower()
            if key not in seen:
                seen.add(key)
                participant_names.append(cleaned_name)

    return participant_names


def _validate_report_form_data(form_data):
    errors = []

    title = form_data['title']
    description = form_data['description']
    category_id = form_data['category_id']
    participant_string = form_data['participants']

    if not title:
        errors.append("Title is required.")
    elif not verify_title(title):
        errors.append("Title must be at least 5 characters long and cannot contain profanity.")

    if not description:
        errors.append("Description is required.")
    elif not verify_description(description):
        errors.append("Description must be at least 10 characters long and cannot contain profanity.")

    category = None
    if not category_id:
        errors.append("Category is required.")
    else:
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            errors.append("Selected category is invalid.")

    participant_names = _parse_participant_names(participant_string)
    for cleaned_name in participant_names:
        if not verify_title(cleaned_name):
            errors.append(
                f"Participant name '{cleaned_name}' must be at least 5 characters long and cannot contain profanity."
            )

    return errors, category, participant_names


def _get_or_create_participants(participant_names, user):
    participant_objects = []

    for full_name in participant_names:
        participant = Participant.objects.filter(name__iexact=full_name).first()
        if not participant:
            participant = Participant.objects.create(name=full_name, user=user)
        participant_objects.append(participant)

    return participant_objects


def _build_report_context(page, dependencies, report=None, form_data=None):
    context = {
        'page': page,
        'categories': dependencies['categories'],
        'committees': dependencies['committees'],
    }

    if report is not None:
        context['report'] = report

    if form_data is not None:
        context['form_data'] = {
            'title': form_data['title'],
            'description': form_data['description'],
            'category_id': form_data['category_id'],
            'committee_ids': form_data['committee_ids'],
            'participants': form_data['participants'],
        }

    return context


def _save_report(report, user, form_data, category, participant_names):
    selected_committees = Committee.objects.filter(id__in=form_data['committee_ids'])
    participant_objects = _get_or_create_participants(participant_names, user)

    with transaction.atomic():
        is_create = report is None

        if is_create:
            report = Report.objects.create(
                user=user,
                title=form_data['title'],
                description=form_data['description'],
                category=category,
                feature_image=form_data['feature_image'] if form_data['feature_image'] else 'default_image.jpg',
            )
        else:
            report.title = form_data['title']
            report.description = form_data['description']
            report.category = category

            if form_data['feature_image']:
                report.feature_image = form_data['feature_image']

            report.save()

        report.committees.set(selected_committees)
        report.participants.set(participant_objects)

    return report


@login_required
def create_report_view(request):
    dependencies = _get_report_form_dependencies()

    if request.method == "POST":
        form_data = _get_report_form_data(request)
        errors, category, participant_names = _validate_report_form_data(form_data)

        if errors:
            for error in errors:
                messages.error(request, error)

            context = _build_report_context(
                page='create-report',
                dependencies=dependencies,
                form_data=form_data,
            )
            return render(request, "users/create_report.html", context)

        try:
            report = _save_report(
                report=None,
                user=request.user,
                form_data=form_data,
                category=category,
                participant_names=participant_names,
            )
            logger.info(
                f"Report '{report.title}' created successfully by user '{request.user.username}' with id {report.id}"
            )
            messages.success(request, "Report created successfully.")
            cache.clear()
            return redirect('users:profile')

        except Exception as e:
            logger.error(
                f"Error occurred while creating report by user '{request.user.username}': {str(e)}"
            )
            messages.error(request, "An error occurred while creating the report.")

            context = _build_report_context(
                page='create-report',
                dependencies=dependencies,
                form_data=form_data,
            )
            return render(request, "users/create_report.html", context)

    context = _build_report_context(
        page='create-report',
        dependencies=dependencies,
    )
    return render(request, "users/create_report.html", context)


@login_required
def edit_report_view(request, pk):
    report = get_object_or_404(Report, id=pk, user=request.user, isActive=True)
    dependencies = _get_report_form_dependencies()

    if request.method == "POST":
        form_data = _get_report_form_data(request)
        errors, category, participant_names = _validate_report_form_data(form_data)

        if errors:
            for error in errors:
                messages.error(request, error)

            context = _build_report_context(
                page='create-report',
                dependencies=dependencies,
                report=report,
                form_data=form_data,
            )
            return render(request, "users/create_report.html", context)

        try:
            report = _save_report(
                report=report,
                user=request.user,
                form_data=form_data,
                category=category,
                participant_names=participant_names,
            )
            logger.info(
                f"Report '{report.title}' updated successfully by user '{request.user.username}' with id {report.id}"
            )
            messages.success(request, "Report updated successfully.")
            cache.clear()
            return redirect('users:profile')

        except Exception as e:
            logger.error(
                f"Error occurred while updating report id {report.id} by user '{request.user.username}': {str(e)}"
            )
            messages.error(request, "An error occurred while updating the report.")

            context = _build_report_context(
                page='create-report',
                dependencies=dependencies,
                report=report,
                form_data=form_data,
            )
            return render(request, "users/create_report.html", context)

    context = _build_report_context(
        page='create-report',
        dependencies=dependencies,
        report=report,
    )
    return render(request, "users/create_report.html", context)


from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render
from django.db import transaction

from .models import UserProfilePic


@login_required
def account_view(request):
    # Ensure profile pic exists
    profile = UserProfilePic.objects.get(user=request.user)
   
   

    active_tab = request.GET.get('tab', 'info')
    if active_tab not in ['info', 'password']:
        active_tab = 'info'

    success = False
    errors = []

    if request.method == "POST":
        action = request.POST.get('action', '').strip()

        # ───────────── UPDATE ACCOUNT INFO ─────────────
        if action == 'update_info':
            active_tab = 'info'

            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()

            avatar = request.FILES.get('avatar')
            delete_avatar = request.POST.get('delete_avatar')

            if not first_name:
                errors.append("First name is required.")

            if not last_name:
                errors.append("Last name is required.")

            if not email:
                errors.append("Email is required.")

            if not errors:
                try:
                    with transaction.atomic():
                        # Update user
                        request.user.first_name = first_name
                        request.user.last_name = last_name
                        request.user.email = email
                        request.user.save()

                        # Handle avatar deletion
                        if delete_avatar:
                            if profile.profilePic:
                                profile.profilePic.delete(save=False)
                            profile.profilePic = "profile_pictures/user.png"

                        # Handle new upload
                        if avatar:
                            profile.profilePic = avatar

                        profile.save()

                    success = True

                    

                except Exception as e:
                    errors.append(f"Error updating account: {str(e)}")

        # ───────────── CHANGE PASSWORD ─────────────
        elif action == 'change_password':
            active_tab = 'password'

            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not current_password:
                errors.append("Current password is required.")

            if not new_password:
                errors.append("New password is required.")

            if not confirm_password:
                errors.append("Please confirm your new password.")

            if current_password and not request.user.check_password(current_password):
                errors.append("Current password is incorrect.")

            if new_password and confirm_password and new_password != confirm_password:
                errors.append("Passwords do not match.")

            # Password strength checks
            if new_password:
                if len(new_password) < 12:
                    errors.append("Password must be at least 12 characters.")
                if not any(c.isupper() for c in new_password):
                    errors.append("Must include uppercase letter.")
                if not any(c.islower() for c in new_password):
                    errors.append("Must include lowercase letter.")
                if not any(c.isdigit() for c in new_password):
                    errors.append("Must include a number.")
                if new_password.isalnum():
                    errors.append("Must include a special character.")

            if not errors:
                try:
                    request.user.set_password(new_password)
                    request.user.save()

                    # keep user logged in
                    update_session_auth_hash(request, request.user)

                    success = True

                except Exception as e:
                    errors.append(f"Error changing password: {str(e)}")

        else:
            errors.append("Invalid action.")

    context = {
        'page': 'account',
        'profile': profile,
        'active_tab': active_tab,
        'success': success,
        'errors': errors,
    }

    return render(request, 'users/account.html', context)