from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .decorators import admin_required
from reports.models import Report, Category, Committee
from users.models import UserProfilePic
from django.core.cache import cache
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render




@admin_required
def adminAccountView(request):
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        user_id = request.POST.get("user_id")

        if action in ["activate", "deactivate"] and user_id:
            target_user = get_object_or_404(User, pk=user_id)

            if target_user == request.user:
                messages.error(request, "You cannot change your own account status from this page.")
                return redirect(request.get_full_path())

            if action == "activate":
                target_user.is_active = True
                target_user.save(update_fields=["is_active"])
                messages.success(request, f"Account '{target_user.username}' activated successfully.")
            elif action == "deactivate":
                target_user.is_active = False
                target_user.save(update_fields=["is_active"])
                messages.success(request, f"Account '{target_user.username}' deactivated successfully.")

            return redirect(request.get_full_path())

    active_tab = request.GET.get("tab", "active").strip().lower()
    if active_tab not in ["active", "inactive"]:
        active_tab = "active"

    q = request.GET.get("q", "").strip()

    users = User.objects.all().select_related("profile_pic").order_by("-date_joined")

    if active_tab == "active":
        users = users.filter(is_active=True)
    else:
        users = users.filter(is_active=False)

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(users, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    admin_profile = getattr(request.user, "profile_pic", None)

    context = {
        "page": "Users",
        "page_obj": page_obj,
        "admin_profile": admin_profile,
        "active_tab": active_tab,
        "q": q,
    }
    return render(request, "administration/admin_accounts.html", context)

@admin_required
def adminReportView(request):
    # Handle soft delete
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        report_id = request.POST.get("report_id")

        if action == "delete" and report_id:
            report = get_object_or_404(Report.objects, pk=report_id, isActive=True)
            report.isActive = False
            report.save(update_fields=["isActive"])
            messages.success(request, f"Report '{report.title}' was removed successfully.")
            cache.clear()  # Clear cache to reflect changes immediately
            return redirect("administration:admin-reports")

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    committee = request.GET.get("committee", "").strip()
    username = request.GET.get("username", "").strip()
    period = request.GET.get("period", "").strip()

    reports = (
        Report.objects
        .filter(isActive=True)
        .select_related("user", "category")
        .prefetch_related("committees", "participants")
        .order_by("-date_of_report", "-created")
    )

    if q:
        reports = reports.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    if category and category != "All":
        reports = reports.filter(category__name=category)

    if committee and committee != "All":
        reports = reports.filter(committees__name=committee)

    if username:
        reports = reports.filter(
            Q(user__username__icontains=username) |
            Q(user__first_name__icontains=username) |
            Q(user__last_name__icontains=username)
        )

    if period:
        now = timezone.now()
        if period == "this_week":
            reports = reports.filter(date_of_report__week=now.isocalendar().week, date_of_report__year=now.year)
        elif period == "this_month":
            reports = reports.filter(date_of_report__month=now.month, date_of_report__year=now.year)
        elif period == "this_year":
            reports = reports.filter(date_of_report__year=now.year)

    reports = reports.distinct()

    paginator = Paginator(reports, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    admin_profile = getattr(request.user, "profile_pic", None)

    context = {
        "page": "Reports",
        "page_obj": page_obj,
        "admin_profile": admin_profile,
        "categories": Category.objects.all().order_by("name"),
        "committees": Committee.objects.all().order_by("name"),
        "q": q,
        "selected_category": category,
        "selected_committee": committee,
        "selected_username": username,
        "selected_period": period,
    }
    return render(request, "administration/admin_reports.html", context)