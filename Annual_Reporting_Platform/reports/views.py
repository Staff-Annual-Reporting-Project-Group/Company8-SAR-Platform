

from datetime import date as date_type, timedelta

from django.shortcuts import render,redirect,get_object_or_404
from django.http.response import HttpResponse
from .models import Report,Committee
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import logging
from django.utils import timezone
from django.db.models import Min
from .pdf_utils import generate_date_range_pdf, generate_my_reports_pdf
from django.core.paginator import Paginator
from django.contrib.auth.models import User


def _parse_annual_range(request):
    """
    Parse date-range params from the request and return a 5-tuple:
      (date_from, date_to, range_type, label, extra_ctx)

    range_type is one of: 'year' | 'academic' | 'custom'
    extra_ctx  is a dict of additional template context keys.
    """
    current_year = timezone.now().year
    range_type = request.GET.get('range_type', 'year')

    if range_type == 'academic':
        raw = request.GET.get('start_year', '')
        start_year = int(raw) if raw.isdigit() else (
            current_year if timezone.now().month >= 8 else current_year - 1
        )
        date_from = date_type(start_year, 8, 1)
        date_to   = date_type(start_year + 1, 7, 31)
        label     = f'Academic Year {start_year}/{start_year + 1}'
        extra     = {'start_year': start_year}

    elif range_type == 'custom':
        df_str = request.GET.get('date_from', f'{current_year}-01-01')
        dt_str = request.GET.get('date_to',   f'{current_year}-12-31')
        try:
            date_from = date_type.fromisoformat(df_str)
            date_to   = date_type.fromisoformat(dt_str)
        except (ValueError, TypeError):
            date_from = date_type(current_year, 1, 1)
            date_to   = date_type(current_year, 12, 31)
        label = (f'{date_from.strftime("%d %B %Y")} \u2013 '
                 f'{date_to.strftime("%d %B %Y")}')
        extra = {
            'date_from_val': date_from.isoformat(),
            'date_to_val':   date_to.isoformat(),
        }

    else:  # 'year'
        raw  = request.GET.get('year', '')
        year = int(raw) if raw.isdigit() else current_year
        date_from = date_type(year, 1, 1)
        date_to   = date_type(year, 12, 31)
        label     = str(year)
        extra     = {'selected_year': year}

    return date_from, date_to, range_type, label, extra

logger = logging.getLogger(__name__)


def _apply_period_filter(queryset, period):
    now = timezone.now().date()
    if period == 'this_week':
        return queryset.filter(date_of_report__gte=now - timedelta(days=7))
    elif period == 'this_month':
        return queryset.filter(date_of_report__year=now.year, date_of_report__month=now.month)
    elif period == 'this_year':
        return queryset.filter(date_of_report__year=now.year)
    return queryset


def index(request):
    reports = (
        Report.objects.active()
        .select_related('user', 'category')
        .prefetch_related('committees', 'participants')
    )

    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.search(q)

    category = request.GET.get('category', '').strip()
    if category and category != 'All':
        reports = reports.filter(category__name=category)

    committee_id = request.GET.get('committee', '').strip()
    selected_committee = None
    if committee_id and committee_id != 'All':
        try:
            selected_committee = Committee.objects.get(pk=committee_id)
            reports = reports.filter(committees=selected_committee)
        except (Committee.DoesNotExist, ValueError):
            pass

    participant = request.GET.get('participant', '').strip()
    if participant:
        reports = reports.filter(participants__name__icontains=participant)

    period = request.GET.get('period', '').strip()
    if period and period != 'Forever':
        reports = _apply_period_filter(reports, period)

    reports = reports.distinct()

    paginator = Paginator(reports, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'committees': Committee.objects.all(),
        'q': q,
        'selected_category': category if category not in ('', 'All') else '',
        'selected_committee': selected_committee,
        'selected_participant': participant,
        'selected_period': period if period not in ('', 'Forever') else '',
    }
    return render(request, 'reports/index.html', context)

def reportView(request, pk):
   # logger.info(f"Fetching report with id {pk} from the database")
    try:

        report = get_object_or_404(Report.objects.active(),pk=pk)


        #logger.debug(f"Found report f{report.title}")
    except Exception as e:
        logger.error(f"Error fetching report with id {pk}: {e}")
        raise

    

    recent_reports = Report.objects.active().exclude(pk=report.pk)[:15]

    context = {
        'report': report,
        'recent_reports': recent_reports
    }
    return render(request,'reports/report_details.html',context)

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Report


def selectedUserReportsView(request, pk):
    selected_user = get_object_or_404(User, pk=pk)

    reports = Report.objects.user_reports(selected_user).order_by('-date_of_report', '-created')

    paginator = Paginator(reports, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Reports this user participated in (but did not author)
    participated_reports = (
        Report.objects.active()
        .filter(participants__user=selected_user)
        .exclude(user=selected_user)
        .select_related('user', 'category')
        .prefetch_related('committees', 'participants')
        .order_by('-date_of_report', '-created')
        .distinct()
    )

    context = {
        'selected_user': selected_user,
        'page_obj': page_obj,
        'participated_reports': participated_reports,
    }

    return render(request, 'reports/selected_user_reports.html', context)


@login_required
def deleteReport(request,pk):
    if request.method != "POST":
        messages.error(request, 'Invalid request method')
        return redirect('users:profile')
    report = Report.objects.get(pk=pk)
    if not report:
       messages.error(request, 'Report does not exists')
       return  redirect('users:profile')
    else:
        if request.user == report.user:
            report.delete()
            messages.success(request,"Report Deleted Successfully")
            logger.info(f"Report '{report.title}' with id {report.id} deleted successfully by user '{request.user.username}'")
            return redirect('users:profile')
        else:
            messages.error(request, 'User was not the owner of the report')
            
    return redirect('users:profile')

       
def annual_report(request):
    current_year = timezone.now().year
    date_from, date_to, range_type, label, extra = _parse_annual_range(request)

    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__gte=date_from, date_of_report__lte=date_to)
                      .active()
                      .order_by('-date_of_report')
    )

    earliest = Report.objects.aggregate(Min('date_of_report'))['date_of_report__min']
    base_year = earliest.year if earliest else current_year
    year_range = list(range(current_year, base_year - 1, -1))

    # Academic year options: each entry is (start_year, "YYYY/YYYY+1")
    acad_default = current_year if timezone.now().month >= 8 else current_year - 1
    academic_years = [(y, f'{y}/{y + 1}') for y in range(acad_default, base_year - 1, -1)]

    context = {
        'reports': reports,
        'year_range': year_range,
        'academic_years': academic_years,
        'committees': Committee.objects.all(),
        'page': 'annual',
        'range_type': range_type,
        'label': label,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        **extra,
    }
    return render(request, 'reports/annual_report.html', context)


def annual_report_pdf(request):
    date_from, date_to, range_type, label, _ = _parse_annual_range(request)
    reports = list(
        Report.objects.select_related('user', 'category')
                      .prefetch_related('committees', 'participants')
                      .filter(date_of_report__gte=date_from, date_of_report__lte=date_to)
                      .active()
                      .order_by('date_of_report')
    )
    buf = generate_date_range_pdf(reports, date_from, date_to, label)
    safe_label = label.replace('/', '-').replace(' ', '_')
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="DCIT_Annual_Report_{safe_label}.pdf"'
    )
    return response

@login_required
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

