import csv
import io
import json
import re
import secrets
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Min, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import admin_required
from reports.models import Category, Committee, Participant, Report
from users.models import UserProfilePic




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




@admin_required
def generateReportsView(request):
    admin_profile = getattr(request.user, "profile_pic", None)

    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]

        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Please upload a .csv file.")
            return redirect("administration:generate-reports")

        try:
            raw = csv_file.read()
            try:
                content = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = raw.decode("latin-1")

            reader = csv.DictReader(io.StringIO(content))
            rows = []

            for i, row in enumerate(reader):
                username = row.get("username", "").strip()
                title = row.get("title", "").strip()
                description = row.get("description", "").strip()
                category_name = row.get("category", "General").strip() or "General"
                date_str = row.get("date_of_report", "").strip()
                committees_raw = row.get("committees", "").strip()
                participants_raw = row.get("participants", "").strip()

                errors = []
                user_display = ""

                if not username:
                    errors.append("Username is required")
                else:
                    try:
                        u = User.objects.get(username=username)
                        full = u.get_full_name()
                        user_display = f"{full} (@{username})" if full else f"@{username}"
                    except User.DoesNotExist:
                        errors.append(f'User "{username}" not found')

                if not title:
                    errors.append("Title is required")
                if not description:
                    errors.append("Description is required")

                if date_str:
                    try:
                        datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        errors.append(f'Invalid date "{date_str}" — use YYYY-MM-DD')
                else:
                    date_str = str(date.today())

                rows.append({
                    "idx": i,
                    "username": username,
                    "user_display": user_display,
                    "title": title,
                    "description": description,
                    "category": category_name,
                    "date_of_report": date_str,
                    "committees": [c.strip() for c in committees_raw.split(";") if c.strip()],
                    "participants": [p.strip() for p in participants_raw.split(";") if p.strip()],
                    "valid": len(errors) == 0,
                    "errors": errors,
                })

            if not rows:
                messages.error(request, "The CSV file contained no data rows.")
                return redirect("administration:generate-reports")

            request.session["csv_report_rows"] = rows
            return redirect("administration:csv-preview-reports")

        except Exception as exc:
            messages.error(request, f"Could not parse CSV: {exc}")
            return redirect("administration:generate-reports")

    current_year = timezone.now().year
    earliest = Report.objects.aggregate(Min("date_of_report"))["date_of_report__min"]
    base_year = earliest.year if earliest else current_year
    year_range = list(range(current_year, base_year - 1, -1))
    acad_default = current_year if timezone.now().month >= 8 else current_year - 1
    academic_years = [(y, f"{y}/{y + 1}") for y in range(acad_default, base_year - 1, -1)]

    context = {
        "page": "Generate Reports",
        "admin_profile": admin_profile,
        "year_range": year_range,
        "academic_years": academic_years,
    }
    return render(request, "administration/admin_generate_reports.html", context)


@admin_required
def csvPreviewReportsView(request):
    """Show a preview of parsed CSV rows; allow removing rows before import."""
    admin_profile = getattr(request.user, "profile_pic", None)
    rows = request.session.get("csv_report_rows", [])

    if not rows:
        messages.error(request, "No CSV data found. Please upload a file first.")
        return redirect("administration:generate-reports")

    if request.method == "POST":
        kept_json = request.POST.get("kept_indices", "[]")
        try:
            kept_set = set(int(x) for x in json.loads(kept_json))
        except (json.JSONDecodeError, ValueError, TypeError):
            kept_set = {r["idx"] for r in rows}

        rows_to_import = [r for r in rows if r["idx"] in kept_set and r["valid"]]

        imported = skipped = errors = 0

        for row in rows_to_import:
            try:
                with transaction.atomic():
                    user = User.objects.get(username=row["username"])
                    category, _ = Category.objects.get_or_create(name=row["category"])

                    if Report.objects.filter(
                        title=row["title"], user=user, isActive=True
                    ).exists():
                        skipped += 1
                        continue

                    try:
                        report_date = datetime.strptime(
                            row["date_of_report"], "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        report_date = date.today()

                    report = Report.objects.create(
                        user=user,
                        title=row["title"],
                        description=row["description"],
                        category=category,
                        date_of_report=report_date,
                        isActive=True,
                    )

                    for comm_name in row["committees"]:
                        committee, _ = Committee.objects.get_or_create(name=comm_name)
                        report.committees.add(committee)

                    for part_name in row["participants"]:
                        participant, _ = Participant.objects.get_or_create(
                            name=part_name
                        )
                        report.participants.add(participant)

                    imported += 1

            except Exception:
                errors += 1

        del request.session["csv_report_rows"]
        cache.clear()

        if errors:
            messages.warning(
                request,
                f"Import complete — {imported} imported, {skipped} skipped (duplicate), {errors} errors.",
            )
        else:
            messages.success(
                request,
                f"Import complete — {imported} imported, {skipped} skipped (duplicate).",
            )
        return redirect("administration:generate-reports")

    context = {
        "page": "Generate Reports",
        "admin_profile": admin_profile,
        "rows": rows,
        "total": len(rows),
        "valid_count": sum(1 for r in rows if r["valid"]),
        "error_count": sum(1 for r in rows if not r["valid"]),
    }
    return render(request, "administration/admin_csv_preview_reports.html", context)


# ── staff CSV helpers ─────────────────────────────────────────────────────────

def _suggest_username(first_name, last_name):
    """Generate a unique username suggestion from a name."""
    base = f'{first_name.lower()}.{last_name.lower()}' if last_name else first_name.lower()
    base = re.sub(r'[^a-z0-9.]', '', base) or 'user'
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


def _find_existing_user(first_name, last_name, email):
    """Return (user, match_reason) if a matching account is found, else (None, '')."""
    if email:
        u = User.objects.filter(email__iexact=email).first()
        if u:
            return u, 'email'
    if first_name and last_name:
        u = User.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
        ).first()
        if u:
            return u, 'name'
    return None, ''


@admin_required
def generateStaffCSVView(request):
    """Accept the staff CSV upload, parse it, store in session, redirect to preview."""
    if request.method != "POST" or not request.FILES.get("staff_csv_file"):
        return redirect("administration:generate-reports")

    csv_file = request.FILES["staff_csv_file"]
    if not csv_file.name.lower().endswith(".csv"):
        messages.error(request, "Please upload a .csv file.")
        return redirect("administration:generate-reports")

    try:
        raw = csv_file.read()
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")

        reader = csv.DictReader(io.StringIO(content))
        rows = []

        for i, row in enumerate(reader):
            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            email = row.get("email", "").strip()
            photo_url = row.get("photo_url", "").strip()

            errors = []
            if not first_name:
                errors.append("First name is required")
            if not last_name:
                errors.append("Last name is required")

            existing, match_reason = _find_existing_user(first_name, last_name, email)

            if existing:
                suggested_username = existing.username
            else:
                suggested_username = _suggest_username(first_name, last_name) if not errors else ""

            rows.append({
                "idx": i,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "photo_url": photo_url,
                "username": suggested_username,
                "existing_id": existing.pk if existing else None,
                "existing_name": f"{existing.get_full_name()} (@{existing.username})" if existing else "",
                "match_reason": match_reason,
                "valid": len(errors) == 0,
                "errors": errors,
            })

        if not rows:
            messages.error(request, "The CSV file contained no data rows.")
            return redirect("administration:generate-reports")

        request.session["csv_staff_rows"] = rows
        return redirect("administration:csv-preview-staff")

    except Exception as exc:
        messages.error(request, f"Could not parse CSV: {exc}")
        return redirect("administration:generate-reports")


@admin_required
def csvPreviewStaffView(request):
    """Show editable preview of staff CSV; handle final import on POST."""
    admin_profile = getattr(request.user, "profile_pic", None)
    rows = request.session.get("csv_staff_rows", [])

    if not rows:
        messages.error(request, "No CSV data found. Please upload a file first.")
        return redirect("administration:generate-reports")

    if request.method == "POST":
        kept_json = request.POST.get("kept_indices", "[]")
        try:
            kept_set = set(int(x) for x in json.loads(kept_json))
        except (json.JSONDecodeError, ValueError, TypeError):
            kept_set = {r["idx"] for r in rows}

        created_count = updated_count = skipped_count = error_count = 0

        for row in rows:
            idx = row["idx"]
            if idx not in kept_set:
                continue

            # Read (potentially edited) values from POST
            first_name = request.POST.get(f"first_name_{idx}", row["first_name"]).strip()
            last_name = request.POST.get(f"last_name_{idx}", row["last_name"]).strip()
            email = request.POST.get(f"email_{idx}", row["email"]).strip()
            username = request.POST.get(f"username_{idx}", row["username"]).strip()
            photo_url = request.POST.get(f"photo_url_{idx}", row["photo_url"]).strip()

            if not first_name or not last_name:
                error_count += 1
                continue

            try:
                with transaction.atomic():
                    existing, _ = _find_existing_user(first_name, last_name, email)

                    if existing:
                        # Update email / reactivate if needed
                        changed = False
                        if email and existing.email != email:
                            existing.email = email
                            changed = True
                        if not existing.is_active:
                            existing.is_active = True
                            changed = True
                        if changed:
                            existing.save()

                        # Set photo only if still on the default
                        if photo_url:
                            profile, _ = UserProfilePic.objects.get_or_create(user=existing)
                            current = str(profile.profilePic)
                            if not current or current == UserProfilePic.DEFAULT_PIC:
                                profile.profilePic = photo_url
                                profile.save(update_fields=["profilePic"])

                        updated_count += 1

                    else:
                        # Resolve username (handle any collision from editing)
                        if not username:
                            username = _suggest_username(first_name, last_name)

                        final_username = username
                        counter = 1
                        while User.objects.filter(username=final_username).exists():
                            final_username = f"{username}{counter}"
                            counter += 1

                        new_user = User.objects.create_user(
                            username=final_username,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            password=secrets.token_urlsafe(20),
                            is_active=True,
                        )

                        if photo_url:
                            profile, _ = UserProfilePic.objects.get_or_create(user=new_user)
                            profile.profilePic = photo_url
                            profile.save(update_fields=["profilePic"])

                        created_count += 1

            except Exception:
                error_count += 1

        del request.session["csv_staff_rows"]

        parts = []
        if created_count: parts.append(f"{created_count} created")
        if updated_count: parts.append(f"{updated_count} updated")
        if skipped_count: parts.append(f"{skipped_count} skipped")
        if error_count: parts.append(f"{error_count} errors")
        summary = ", ".join(parts) or "nothing processed"

        if error_count:
            messages.warning(request, f"Staff import complete — {summary}.")
        else:
            messages.success(request, f"Staff import complete — {summary}.")

        return redirect("administration:generate-reports")

    context = {
        "page": "Generate Reports",
        "admin_profile": admin_profile,
        "rows": rows,
        "total": len(rows),
        "new_count": sum(1 for r in rows if not r["existing_id"] and r["valid"]),
        "exists_count": sum(1 for r in rows if r["existing_id"]),
        "error_count": sum(1 for r in rows if not r["valid"]),
    }
    return render(request, "administration/admin_csv_preview_staff.html", context)