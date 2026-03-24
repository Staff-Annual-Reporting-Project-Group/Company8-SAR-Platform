from django.db import models
from django.contrib.auth.models import User
import django.utils.timezone as timezone
class ReportManager(models.Manager):
    def all(self):
        return self.filter(state__icontains='Approved')
    def all_submitted(self):
        return self.filter(state__icontains='Submitted')
    
    

    def user_reports(self,user):
        return self.filter(user=user)
    
    def search(self,keyword):
        return self.all().filter(title__icontains=keyword)
    
    def filterReports(self,period,report_type, committee, participant):
        queryset = self.all()
        period = str(period).lower().strip() if period != None else None
        if period:
            if period == 'forever':
                queryset =  queryset
            elif period == 'this_week':
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