from functools import wraps
from datetime import timedelta, date

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Min, Q

from .models import Report, Committee, Category, Participant, StaffProfile
from .pdf_utils import generate_annual_pdf, generate_my_reports_pdf
from .cloudinary_storage import upload_avatar, upload_report_image, delete_image


# -- helpers --

def _committees():
    return Committee.objects.all()

def _apply_period_filter(queryset, period):
    now = timezone.now().date()
    if period == 'this_week':
        return queryset.filter(date_of_report__gte=now - timedelta(days=7))
    elif period == 'this_month':
        return queryset.filter(date_of_report__year=now.year, date_of_report__month=now.month)
    elif period == 'this_year':
        return queryset.filter(date_of_report__year=now.year)
    return queryset


# -- admin decorator --

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('reports:login')
        if not (request.user.is_staff or request.user.is_superuser):
            return HttpResponseForbidden('Admin access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


# -- index --

def index(request):
    reports = Report.objects.filter(status=Report.STATUS_APPROVED) \
                            .select_related('user', 'category') \
                            .prefetch_related('committees', 'participants') \
                            .order_by('-date_of_report')

    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(title__icontains=q)

    category = request.GET.get('type', '').strip()
    if category:
        reports = reports.filter(category__name__iexact=category)

    committee_id = request.GET.get('committee', '').strip()
    if committee_id:
        reports = reports.filter(committees__id=committee_id)

    participant = request.GET.get('participant', '').strip()
    if participant:
        reports = reports.filter(participants__name__icontains=participant)

    period = request.GET.get('period', '').strip()
    if period:
        reports = _apply_period_filter(reports, period)

    return render(request, 'reports/index.html', {
        'reports': reports,
        'committees': _committees(),
    })


# -- report detail --

def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants'),
        pk=pk,
    )

    # Block access to non-approved reports unless the viewer is the owner or admin
    is_owner = request.user.is_authenticated and request.user == report.user
    is_admin = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
    if report.status != Report.STATUS_APPROVED and not is_owner and not is_admin:
        from django.http import Http404
        raise Http404

    recent_reports = (
        Report.objects.filter(status=Report.STATUS_APPROVED)
                      .select_related('user', 'category')
                      .prefetch_related('committees')
                      .order_by('-date_of_report')
                      .exclude(pk=pk)[:10]
    )
    return render(request, 'reports/report_detail.html', {
        'report': report,
        'recent_reports': recent_reports,
        'committees': _committees(),
    })


# -- annual report --

def annual_report(request):
    current_year = timezone.now().year
    year = int(request.GET.get('year', current_year))

    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__year=year)
                      .order_by('-date_of_report')
    )

    earliest = Report.objects.aggregate(Min('date_of_report'))['date_of_report__min']
    start_year = earliest.year if earliest else current_year
    year_range = range(current_year, start_year - 1, -1)

    return render(request, 'reports/annual_report.html', {
        'reports': reports,
        'year': year,
        'year_range': year_range,
        'committees': _committees(),
    })


# -- annual report PDF --

def annual_report_pdf(request):
    current_year = timezone.now().year
    year = int(request.GET.get('year', current_year))
    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__year=year)
                      .order_by('date_of_report')
    )
    buf = generate_annual_pdf(reports, year)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DCIT_Annual_Report_{year}.pdf"'
    return response


# -- my reports PDF --

@login_required(login_url='reports:login')
def my_reports_pdf(request):
    reports = list(
        Report.objects.select_related('category')
                      .prefetch_related('committees', 'participants')
                      .filter(user=request.user)
                      .order_by('date_of_report')
    )
    buf = generate_my_reports_pdf(reports, request.user)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="My_Reports_{request.user.username}.pdf"'
    return response


# -- profile --

@login_required(login_url='reports:login')
def profile(request):
    reports = Report.objects.filter(user=request.user) \
                            .select_related('category') \
                            .prefetch_related('committees', 'participants') \
                            .order_by('-date_of_report')

    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(title__icontains=q)

    category = request.GET.get('type', '').strip()
    if category:
        reports = reports.filter(category__name__iexact=category)

    period = request.GET.get('period', '').strip()
    if period:
        reports = _apply_period_filter(reports, period)

    return render(request, 'reports/profile.html', {
        'reports': reports,
        'categories': Category.objects.all(),
        'committees': _committees(),
    })


# -- account --

@login_required(login_url='reports:login')
def account(request):
    profile, _ = StaffProfile.objects.get_or_create(user=request.user)
    errors = []
    success = False
    active_tab = request.GET.get('tab', 'info')

    if request.method == 'POST':
        action = request.POST.get('action')
        active_tab = 'info' if action == 'update_info' else 'password'

        if action == 'update_info':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            bio = request.POST.get('bio', '').strip()
            phone = request.POST.get('phone', '').strip()
            gender = request.POST.get('gender', '').strip()

            if not first_name:
                errors.append('First name is required.')
            if not email:
                errors.append('Email is required.')
            elif User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                errors.append('That email is already used by another account.')

            if not errors:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.save()
                profile.bio = bio
                profile.phone = phone
                profile.gender = gender
                if request.FILES.get('avatar'):
                    if profile.avatar:
                        delete_image(profile.avatar)
                    profile.avatar = upload_avatar(request.FILES['avatar'])
                if request.POST.get('delete_avatar') and profile.avatar:
                    delete_image(profile.avatar)
                    profile.avatar = None
                profile.save()
                success = True

        elif action == 'change_password':
            current = request.POST.get('current_password', '')
            new_pw = request.POST.get('new_password', '')
            confirm = request.POST.get('confirm_password', '')

            if not request.user.check_password(current):
                errors.append('Current password is incorrect.')
            elif len(new_pw) < 12:
                errors.append('Password must be at least 12 characters.')
            elif not any(c.isupper() for c in new_pw):
                errors.append('Password must contain at least one uppercase character.')
            elif not any(c.islower() for c in new_pw):
                errors.append('Password must contain at least one lowercase character.')
            elif not any(c.isdigit() for c in new_pw):
                errors.append('Password must contain at least one number.')
            elif not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in new_pw):
                errors.append('Password must contain at least one special character.')
            elif new_pw != confirm:
                errors.append('New passwords do not match.')

            if not errors:
                request.user.set_password(new_pw)
                request.user.save()
                update_session_auth_hash(request, request.user)
                success = True

    return render(request, 'reports/account.html', {
        'profile': profile,
        'errors': errors,
        'success': success,
        'active_tab': active_tab,
        'committees': _committees(),
    })


# -- create report --

@login_required(login_url='reports:login')
def create_report(request):
    committees = _committees()
    categories = Category.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        committee_ids = request.POST.getlist('committees')
        category_id = request.POST.get('category')
        date_str = request.POST.get('date_of_report', '').strip()
        participant_names = request.POST.getlist('participants')
        feature_image = request.FILES.get('feature_image')

        errors = []
        if not title:
            errors.append('Report title is required.')
        if not description:
            errors.append('Description is required.')

        if errors:
            return render(request, 'reports/create_report.html', {
                'errors': errors,
                'committees': committees,
                'categories': categories,
                'form_data': request.POST,
            })

        report = Report(user=request.user, title=title, description=description)
        if category_id:
            report.category = Category.objects.filter(id=category_id).first()
        if date_str:
            try:
                report.date_of_report = date.fromisoformat(date_str)
            except ValueError:
                pass
        if feature_image:
            report.feature_image = upload_report_image(feature_image)
        report.save()

        if committee_ids:
            report.committees.set(Committee.objects.filter(id__in=committee_ids))

        for item in participant_names:
            item = item.strip()
            if not item:
                continue
            # Format: "Full Name::username" when selected from dropdown, else plain name
            if '::' in item:
                name, username = item.split('::', 1)
                linked_user = User.objects.filter(username=username).first()
            else:
                name = item
                linked_user = None
            p, _ = Participant.objects.get_or_create(name=name)
            if linked_user:
                p.user = linked_user
                p.save(update_fields=['user'])
            report.participants.add(p)

        return redirect('reports:profile')

    return render(request, 'reports/create_report.html', {
        'committees': committees,
        'categories': categories,
    })


# -- edit report --

@login_required(login_url='reports:login')
def edit_report(request, pk):
    report = get_object_or_404(Report, pk=pk, user=request.user)
    committees = _committees()
    categories = Category.objects.all()

    if request.method == 'POST':
        report.title = request.POST.get('title', report.title).strip()
        report.description = request.POST.get('description', report.description).strip()

        category_id = request.POST.get('category')
        report.category = Category.objects.filter(id=category_id).first() if category_id else None

        date_str = request.POST.get('date_of_report', '').strip()
        if date_str:
            try:
                report.date_of_report = date.fromisoformat(date_str)
            except ValueError:
                pass

        if request.FILES.get('feature_image'):
            if report.feature_image:
                delete_image(report.feature_image)
            report.feature_image = upload_report_image(request.FILES['feature_image'])
        elif request.POST.get('delete_image'):
            if report.feature_image:
                delete_image(report.feature_image)
            report.feature_image = None

        # Reset to pending whenever an approved report is edited
        if report.status == Report.STATUS_APPROVED:
            report.status = Report.STATUS_PENDING

        report.save()

        committee_ids = request.POST.getlist('committees')
        report.committees.set(Committee.objects.filter(id__in=committee_ids))

        report.participants.clear()
        for item in request.POST.getlist('participants'):
            item = item.strip()
            if not item:
                continue
            if '::' in item:
                name, username = item.split('::', 1)
                linked_user = User.objects.filter(username=username).first()
            else:
                name = item
                linked_user = None
            p, _ = Participant.objects.get_or_create(name=name)
            if linked_user:
                p.user = linked_user
                p.save(update_fields=['user'])
            report.participants.add(p)

        return redirect('reports:profile')

    return render(request, 'reports/create_report.html', {
        'report': report,
        'committees': committees,
        'categories': categories,
        'editing': True,
    })


# -- delete report --

@login_required(login_url='reports:login')
def delete_report(request, pk):
    report = get_object_or_404(Report, pk=pk, user=request.user)
    if request.method == 'POST':
        if report.feature_image:
            delete_image(report.feature_image)
        report.delete()
    return redirect('reports:profile')


# -- admin dashboard --

@admin_required
def admin_dashboard(request):
    pending_accounts = StaffProfile.objects.filter(
        is_approved=False, user__is_active=False
    ).select_related('user').order_by('requested_at')

    pending_reports = Report.objects.filter(
        status=Report.STATUS_PENDING
    ).select_related('user', 'category').prefetch_related('committees').order_by('-created')

    all_reports = Report.objects.select_related('user', 'category') \
                                .prefetch_related('committees') \
                                .order_by('-created')

    status_filter = request.GET.get('status', '')
    if status_filter:
        all_reports = all_reports.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        all_reports = all_reports.filter(title__icontains=q)

    current_year = timezone.now().year
    current_ay_start = current_year if timezone.now().month >= 8 else current_year - 1
    earliest = Report.objects.aggregate(Min('date_of_report'))['date_of_report__min']
    earliest_year = earliest.year if earliest else current_ay_start
    ay_range = range(current_ay_start, earliest_year - 1, -1)

    all_users = User.objects.select_related('profile') \
                            .order_by('first_name', 'last_name')

    active_tab = request.GET.get('tab', 'accounts')

    return render(request, 'reports/admin_dashboard.html', {
        'pending_accounts': pending_accounts,
        'pending_reports': pending_reports,
        'all_reports': all_reports,
        'all_users': all_users,
        'status_filter': status_filter,
        'active_tab': active_tab,
        'q': q,
        'ay_range': ay_range,
        'committees': _committees(),
        'stats': {
            'pending_accounts': pending_accounts.count(),
            'pending_reports': Report.objects.filter(status=Report.STATUS_PENDING).count(),
            'total_users': User.objects.filter(is_active=True).count(),
            'total_reports': Report.objects.count(),
            'approved_reports': Report.objects.filter(status=Report.STATUS_APPROVED).count(),
            'declined_reports': Report.objects.filter(status=Report.STATUS_DECLINED).count(),
        },
    })


@admin_required
def admin_delete_user(request, user_id):
    if request.method != 'POST':
        return redirect('reports:admin_dashboard')
    user = get_object_or_404(User, id=user_id)
    # Prevent self-deletion
    if user == request.user:
        return redirect('reports:admin_dashboard')
    # Delete Cloudinary images before removing the user
    if hasattr(user, 'profile') and user.profile.avatar:
        delete_image(user.profile.avatar)
    for report in user.report_set.all():
        if report.feature_image:
            delete_image(report.feature_image)
    user.delete()
    return redirect('reports:admin_dashboard')



    if request.method == 'POST':
        for p in StaffProfile.objects.filter(is_approved=False, user__is_active=False):
            p.approve()
    return redirect('reports:admin_dashboard')


@admin_required
def admin_approve_all_accounts(request):
    if request.method == 'POST':
        for p in StaffProfile.objects.filter(is_approved=False, user__is_active=False):
            p.approve()
    return redirect('reports:admin_dashboard')


@admin_required
def admin_approve_all_reports(request):
    if request.method == 'POST':
        Report.objects.filter(status=Report.STATUS_PENDING).update(status=Report.STATUS_APPROVED)
    return redirect('reports:admin_dashboard')


@admin_required
def admin_account_action(request, user_id):
    if request.method != 'POST':
        return redirect('reports:admin_dashboard')
    profile = get_object_or_404(StaffProfile, user__id=user_id)
    action = request.POST.get('action')
    if action == 'approve':
        profile.approve()
    elif action == 'deny':
        profile.deny()
    return redirect('reports:admin_dashboard')


@admin_required
def admin_report_action(request, pk):
    if request.method != 'POST':
        return redirect('reports:admin_dashboard')
    report = get_object_or_404(Report, pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        report.status = Report.STATUS_APPROVED
        report.save(update_fields=['status'])
    elif action == 'decline':
        report.status = Report.STATUS_DECLINED
        report.save(update_fields=['status'])
    elif action == 'delete':
        if report.feature_image:
            delete_image(report.feature_image)
        report.delete()
    return redirect(request.POST.get('next', 'reports:admin_dashboard'))


@admin_required
def admin_academic_pdf(request):
    try:
        start_year = int(request.GET.get('ay', timezone.now().year))
    except ValueError:
        start_year = timezone.now().year

    date_from = date(start_year, 8, 1)
    date_to = date(start_year + 1, 7, 31)

    reports = list(
        Report.objects.filter(
            date_of_report__gte=date_from,
            date_of_report__lte=date_to,
            status=Report.STATUS_APPROVED,
        ).select_related('user', 'category')
         .prefetch_related('committees', 'participants')
         .order_by('date_of_report')
    )

    from .pdf_utils import generate_academic_pdf
    buf = generate_academic_pdf(reports, start_year)
    filename = f"DCIT_Academic_Report_{start_year}_{start_year + 1}.pdf"
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# -- public user profile --

def user_profile(request, username):
    viewed_user = get_object_or_404(User, username=username)
    profile, _ = StaffProfile.objects.get_or_create(user=viewed_user)

    # Reports created by this user
    created_reports = Report.objects.filter(
        user=viewed_user, status='approved'
    ).select_related('category').prefetch_related('committees', 'participants') \
     .order_by('-date_of_report')

    # Reports where this user appears as a participant (but didn't create)
    participated_reports = Report.objects.filter(
        participants__user=viewed_user,
        status='approved',
    ).exclude(user=viewed_user) \
     .select_related('user', 'category').prefetch_related('committees', 'participants') \
     .order_by('-date_of_report')

    return render(request, 'reports/user_profile.html', {
        'viewed_user': viewed_user,
        'profile': profile,
        'created_reports': created_reports,
        'participated_reports': participated_reports,
        'is_own': request.user == viewed_user,
        'committees': _committees(),
    })


# -- user search API (autocomplete) --

import json as _json

def user_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return HttpResponse('[]', content_type='application/json')

    users = User.objects.filter(is_active=True).filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(username__icontains=q)
    ).values('id', 'username', 'first_name', 'last_name')[:10]

    results = [
        {
            'username': u['username'],
            'name': f"{u['first_name']} {u['last_name']}".strip() or u['username'],
        }
        for u in users
    ]
    return HttpResponse(_json.dumps(results), content_type='application/json')


# -- register --

def register_view(request):
    if request.user.is_authenticated:
        return redirect('reports:profile')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        errors = []
        field_errors = set()

        if not first_name:
            errors.append('First name is required.'); field_errors.add('first_name')
        if not last_name:
            errors.append('Last name is required.'); field_errors.add('last_name')
        if not username:
            errors.append('Username is required.'); field_errors.add('username')
        elif User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" is taken.'); field_errors.add('username')
        if not email:
            errors.append('Email is required.'); field_errors.add('email')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already in use.'); field_errors.add('email')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.'); field_errors.add('password')
        if password != password2:
            errors.append('Passwords do not match.'); field_errors.add('password2')

        if errors:
            return render(request, 'reports/register.html', {
                'errors': errors,
                'field_errors': field_errors,
                'form_data': {
                    'first_name': first_name, 'last_name': last_name,
                    'username': username, 'email': email,
                },
                'committees': _committees(),
            })

        User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
            is_active=False,
        )
        return render(request, 'reports/register.html', {
            'pending': True,
            'committees': _committees(),
        })

    return render(request, 'reports/register.html', {'committees': _committees()})


# -- login / logout --

def login_view(request):
    if request.user.is_authenticated:
        return redirect('reports:profile')

    error = None

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(60 * 60 * 24 * 30)
            next_url = request.POST.get('next') or request.GET.get('next') or 'reports:profile'
            return redirect(next_url)

        try:
            u = User.objects.get(username=username)
            error = 'Incorrect password.' if u.is_active else 'Account pending approval.'
        except User.DoesNotExist:
            error = 'No account found with that username.'

        return render(request, 'reports/login.html', {
            'error': error,
            'saved_username': username,
            'committees': _committees(),
        })

    return render(request, 'reports/login.html', {'committees': _committees()})


def logout_view(request):
    logout(request)
    return redirect('reports:login')
