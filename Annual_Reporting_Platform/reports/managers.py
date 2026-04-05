from django.db import models
from django.utils import timezone
from django.db.models import Q

class ReportQuerySet(models.QuerySet):

    def active(self):
        return self.filter(isActive=True)

    def user_reports(self, user):
        return self.filter(user=user)

    def search(self, keyword):
        return self.filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword)
        )

    def filterReports(self, period=None, report_type=None, committee=None, participant=None):
        queryset = self

        if period:
            period = str(period).lower().strip()

            if period == 'this_week':
                queryset = queryset.filter(date_of_report__week=timezone.now().isocalendar().week)
            elif period == 'this_month':
                queryset = queryset.filter(date_of_report__month=timezone.now().month)
            elif period == 'this_year':
                queryset = queryset.filter(date_of_report__year=timezone.now().year)

        if report_type:
            queryset = queryset.filter(category__name=report_type)

        if committee:
            queryset = queryset.filter(committees__name=committee)

        if participant:
            queryset = queryset.filter(participants__name=participant)

        return queryset.distinct()