from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from .models import Report, Committee, Category, Participant, StaffProfile
from .pdf_utils import generate_annual_pdf, generate_my_reports_pdf


# ─────────────────────────────────────────────
#  Index / Report List
# ─────────────────────────────────────────────

def index(request):
    reports = Report.objects.select_related('user', 'category') \
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
        now = timezone.now().date()
        if period == 'this_week':
            reports = reports.filter(date_of_report__gte=now - timedelta(days=7))
        elif period == 'this_month':
            reports = reports.filter(date_of_report__year=now.year,
                                     date_of_report__month=now.month)
        elif period == 'this_year':
            reports = reports.filter(date_of_report__year=now.year)

    committees = Committee.objects.all()

    return render(request, 'reports/index.html', {
        'reports': reports,
        'committees': committees,
    })


# ─────────────────────────────────────────────
#  Report Detail
# ─────────────────────────────────────────────

def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants'),
        pk=pk,
    )
    recent_reports = (
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees')
                      .order_by('-date_of_report')
                      .exclude(pk=pk)[:10]
    )
    return render(request, 'reports/report_detail.html', {
        'report':         report,
        'recent_reports': recent_reports,
        'committees':     Committee.objects.all(),
    })


# ─────────────────────────────────────────────
#  Annual Report
# ─────────────────────────────────────────────

def annual_report(request):
    from django.db.models import Min
    current_year = timezone.now().year
    year = int(request.GET.get('year', current_year))

    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__year=year)
                      .order_by('-date_of_report')
    )

    # Build full year range from earliest report year to current
    earliest = Report.objects.aggregate(Min('date_of_report'))['date_of_report__min']
    start_year = earliest.year if earliest else current_year
    year_range = range(current_year, start_year - 1, -1)

    return render(request, 'reports/annual_report.html', {
        'reports':    reports,
        'year':       year,
        'year_range': year_range,
        'committees': Committee.objects.all(),
    })


# ─────────────────────────────────────────────
#  Annual Report PDF
# ─────────────────────────────────────────────

def annual_report_pdf(request):
    current_year = timezone.now().year
    year = int(request.GET.get('year', current_year))
    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__year=year)
                      .order_by('date_of_report')
    )
    pdf_buffer = generate_annual_pdf(reports, year)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DCIT_Annual_Report_{year}.pdf"'
    return response


# ─────────────────────────────────────────────
#  My Reports PDF
# ─────────────────────────────────────────────

@login_required(login_url='reports:login')
def my_reports_pdf(request):
    reports = list(
        Report.objects.select_related('category')
                      .prefetch_related('committees', 'participants')
                      .filter(user=request.user)
                      .order_by('date_of_report')
    )
    pdf_buffer = generate_my_reports_pdf(reports, request.user)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="My_Reports_{request.user.username}.pdf"'
    return response


# ─────────────────────────────────────────────
#  Profile — My Reports
# ─────────────────────────────────────────────

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
        now = timezone.now().date()
        if period == 'this_week':
            reports = reports.filter(date_of_report__gte=now - timedelta(days=7))
        elif period == 'this_month':
            reports = reports.filter(date_of_report__year=now.year,
                                     date_of_report__month=now.month)
        elif period == 'this_year':
            reports = reports.filter(date_of_report__year=now.year)

    categories = Category.objects.all()
    committees = Committee.objects.all()

    return render(request, 'reports/profile.html', {
        'reports':    reports,
        'categories': categories,
        'committees': committees,
    })


# ─────────────────────────────────────────────
#  Account Information
# ─────────────────────────────────────────────

@login_required(login_url='reports:login')
def account(request):
    profile, _ = StaffProfile.objects.get_or_create(user=request.user)
    errors     = []
    success    = False
    active_tab = request.GET.get('tab', 'info')

    if request.method == 'POST':
        action     = request.POST.get('action')
        active_tab = 'info' if action == 'update_info' else 'password'

        if action == 'update_info':
            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name',  '').strip()
            email      = request.POST.get('email',      '').strip()
            bio        = request.POST.get('bio',        '').strip()
            phone      = request.POST.get('phone',      '').strip()
            gender     = request.POST.get('gender',     '').strip()

            if not first_name:
                errors.append('First name is required.')
            if not email:
                errors.append('Email is required.')
            elif User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                errors.append('That email is already used by another account.')

            if not errors:
                request.user.first_name = first_name
                request.user.last_name  = last_name
                request.user.email      = email
                request.user.save()
                profile.bio    = bio
                profile.phone  = phone
                profile.gender = gender
                if request.FILES.get('avatar'):
                    profile.avatar = request.FILES['avatar']
                if request.POST.get('delete_avatar') and profile.avatar:
                    profile.avatar.delete(save=False)
                    profile.avatar = None
                profile.save()
                success = True

        elif action == 'change_password':
            current = request.POST.get('current_password', '')
            new_pw  = request.POST.get('new_password',     '')
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
        'profile':    profile,
        'errors':     errors,
        'success':    success,
        'active_tab': active_tab,
        'committees': Committee.objects.all(),
    })


# ─────────────────────────────────────────────
#  Create Report
# ─────────────────────────────────────────────

@login_required(login_url='reports:login')
def create_report(request):
    committees = Committee.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        title             = request.POST.get('title', '').strip()
        description       = request.POST.get('description', '').strip()
        committee_ids     = request.POST.getlist('committees')
        category_id       = request.POST.get('category')
        date_str          = request.POST.get('date_of_report', '').strip()
        participant_names = request.POST.getlist('participants')
        feature_image     = request.FILES.get('feature_image')

        errors = []
        if not title:
            errors.append('Report title is required.')
        if not description:
            errors.append('Description is required.')

        if errors:
            return render(request, 'reports/create_report.html', {
                'errors': errors, 'committees': committees,
                'categories': categories, 'form_data': request.POST,
            })

        report = Report(user=request.user, title=title, description=description)
        if category_id:
            report.category = Category.objects.filter(id=category_id).first()
        if date_str:
            from datetime import date
            try:
                report.date_of_report = date.fromisoformat(date_str)
            except ValueError:
                pass
        if feature_image:
            report.feature_image = feature_image
        report.save()

        if committee_ids:
            report.committees.set(Committee.objects.filter(id__in=committee_ids))

        for name in participant_names:
            name = name.strip()
            if name:
                p, _ = Participant.objects.get_or_create(name=name)
                report.participants.add(p)

        return redirect('reports:profile')

    return render(request, 'reports/create_report.html', {
        'committees': committees,
        'categories': categories,
    })


# ─────────────────────────────────────────────
#  Edit Report
# ─────────────────────────────────────────────

@login_required(login_url='reports:login')
def edit_report(request, pk):
    report     = get_object_or_404(Report, pk=pk, user=request.user)
    committees = Committee.objects.all()
    categories = Category.objects.all()

    if request.method == 'POST':
        report.title       = request.POST.get('title', report.title).strip()
        report.description = request.POST.get('description', report.description).strip()

        category_id = request.POST.get('category')
        report.category = Category.objects.filter(id=category_id).first() if category_id else None

        date_str = request.POST.get('date_of_report', '').strip()
        if date_str:
            from datetime import date
            try:
                report.date_of_report = date.fromisoformat(date_str)
            except ValueError:
                pass

        # Image handling
        if request.FILES.get('feature_image'):
            report.feature_image = request.FILES['feature_image']
        elif request.POST.get('delete_image'):
            if report.feature_image:
                report.feature_image.delete(save=False)
            report.feature_image = None

        report.save()

        committee_ids = request.POST.getlist('committees')
        report.committees.set(Committee.objects.filter(id__in=committee_ids))

        report.participants.clear()
        for name in request.POST.getlist('participants'):
            name = name.strip()
            if name:
                p, _ = Participant.objects.get_or_create(name=name)
                report.participants.add(p)

        return redirect('reports:profile')

    return render(request, 'reports/create_report.html', {
        'report': report,
        'committees': committees,
        'categories': categories,
        'editing': True,
    })


# ─────────────────────────────────────────────
#  Delete Report
# ─────────────────────────────────────────────

@login_required(login_url='reports:login')
def delete_report(request, pk):
    report = get_object_or_404(Report, pk=pk, user=request.user)
    if request.method == 'POST':
        report.delete()
    return redirect('reports:profile')


# ─────────────────────────────────────────────
#  Admin Dashboard helpers
# ─────────────────────────────────────────────

def admin_required(view_func):
    """Decorator: staff or superuser only."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('reports:login')
        if not (request.user.is_staff or request.user.is_superuser):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('Admin access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    pending_accounts = StaffProfile.objects.filter(
        is_approved=False, user__is_active=False
    ).select_related('user').order_by('requested_at')

    pending_reports  = Report.objects.filter(
        status=Report.STATUS_PENDING
    ).select_related('user', 'category').prefetch_related('committees').order_by('-created')

    all_reports = Report.objects.select_related('user', 'category') \
                                .prefetch_related('committees') \
                                .order_by('-created')

    # Filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        all_reports = all_reports.filter(status=status_filter)

    q = request.GET.get('q', '').strip()
    if q:
        all_reports = all_reports.filter(title__icontains=q)

    # Academic year range for PDF dropdown
    current_year = timezone.now().year
    # Academic year starts Aug 1; if current month >= 8 the new AY has started
    current_ay_start = current_year if timezone.now().month >= 8 else current_year - 1
    from django.db.models import Min
    earliest = Report.objects.aggregate(Min('date_of_report'))['date_of_report__min']
    earliest_year = earliest.year if earliest else current_ay_start
    # Build list of academic year start years
    ay_range = range(current_ay_start, earliest_year - 1, -1)

    return render(request, 'reports/admin_dashboard.html', {
        'pending_accounts': pending_accounts,
        'pending_reports':  pending_reports,
        'all_reports':      all_reports,
        'status_filter':    status_filter,
        'q':                q,
        'ay_range':         ay_range,
        'committees':       Committee.objects.all(),
        'stats': {
            'pending_accounts': pending_accounts.count(),
            'pending_reports':  Report.objects.filter(status=Report.STATUS_PENDING).count(),
            'total_users':      User.objects.filter(is_active=True).count(),
            'total_reports':    Report.objects.count(),
            'approved_reports': Report.objects.filter(status=Report.STATUS_APPROVED).count(),
            'declined_reports': Report.objects.filter(status=Report.STATUS_DECLINED).count(),
        },
    })


@admin_required
def admin_approve_all_accounts(request):
    if request.method == 'POST':
        pending = StaffProfile.objects.filter(is_approved=False, user__is_active=False)
        for p in pending:
            p.approve()
    return redirect('reports:admin_dashboard')


@admin_required
def admin_approve_all_reports(request):
    if request.method == 'POST':
        Report.objects.filter(status=Report.STATUS_PENDING).update(
            status=Report.STATUS_APPROVED
        )
    return redirect('reports:admin_dashboard')


@admin_required
def admin_account_action(request, user_id):
    """Approve or deny a user account."""
    if request.method != 'POST':
        return redirect('reports:admin_dashboard')
    action  = request.POST.get('action')
    profile = get_object_or_404(StaffProfile, user__id=user_id)
    if action == 'approve':
        profile.approve()
    elif action == 'deny':
        profile.deny()
    return redirect('reports:admin_dashboard')


@admin_required
def admin_report_action(request, pk):
    """Approve, decline, or delete a report."""
    if request.method != 'POST':
        return redirect('reports:admin_dashboard')
    action = request.POST.get('action')
    report = get_object_or_404(Report, pk=pk)
    if action == 'approve':
        report.status = Report.STATUS_APPROVED
        report.save(update_fields=['status'])
    elif action == 'decline':
        report.status = Report.STATUS_DECLINED
        report.save(update_fields=['status'])
    elif action == 'delete':
        report.delete()
    return redirect(request.POST.get('next', 'reports:admin_dashboard'))


@admin_required
def admin_academic_pdf(request):
    """Download academic year PDF (Aug 1 – Jul 31)."""
    try:
        start_year = int(request.GET.get('ay', timezone.now().year))
    except ValueError:
        start_year = timezone.now().year

    from datetime import date
    date_from = date(start_year,     8, 1)
    date_to   = date(start_year + 1, 7, 31)

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


# ─────────────────────────────────────────────
#  Public User Profile
# ─────────────────────────────────────────────

def user_profile(request, username):
    viewed_user = get_object_or_404(User, username=username)
    profile, _  = StaffProfile.objects.get_or_create(user=viewed_user)

    # Only show approved reports on public profiles
    reports = Report.objects.filter(
        user=viewed_user, status='approved'
    ).select_related('category').prefetch_related('committees', 'participants') \
     .order_by('-date_of_report')

    return render(request, 'reports/user_profile.html', {
        'viewed_user': viewed_user,
        'profile':     profile,
        'reports':     reports,
        'is_own':      request.user == viewed_user,
        'committees':  Committee.objects.all(),
    })


# ─────────────────────────────────────────────
#  Register
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('reports:profile')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name',  '').strip()
        username   = request.POST.get('username',   '').strip()
        email      = request.POST.get('email',      '').strip()
        password   = request.POST.get('password',   '')
        password2  = request.POST.get('password2',  '')

        errors       = []
        field_errors = set()

        if not first_name:
            errors.append('First name is required.'); field_errors.add('first_name')
        if not last_name:
            errors.append('Last name is required.');  field_errors.add('last_name')
        if not username:
            errors.append('Username is required.');   field_errors.add('username')
        elif User.objects.filter(username=username).exists():
            errors.append(f'Username "{username}" is taken.'); field_errors.add('username')
        if not email:
            errors.append('Email is required.');      field_errors.add('email')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already in use.');   field_errors.add('email')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.'); field_errors.add('password')
        if password != password2:
            errors.append('Passwords do not match.'); field_errors.add('password2')

        if errors:
            return render(request, 'reports/register.html', {
                'errors': errors, 'field_errors': field_errors,
                'form_data': {
                    'first_name': first_name, 'last_name': last_name,
                    'username': username,     'email': email,
                },
                'committees': Committee.objects.all(),
            })

        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name,
            is_active=False,   # inactive until admin approves
        )
        # StaffProfile auto-created by signal; is_approved stays False
        return render(request, 'reports/register.html', {
            'pending': True,
            'committees': Committee.objects.all(),
        })

    return render(request, 'reports/register.html', {'committees': Committee.objects.all()})


# ─────────────────────────────────────────────
#  Login / Logout
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('reports:profile')

    error = None

    if request.method == 'POST':
        username    = request.POST.get('username', '').strip()
        password    = request.POST.get('password', '')
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
            'error': error, 'saved_username': username,
            'committees': Committee.objects.all(),
        })

    return render(request, 'reports/login.html', {'committees': Committee.objects.all()})


def logout_view(request):
    logout(request)
    return redirect('reports:login')
