

from django.shortcuts import render
from django.http.response import HttpResponse
from .models import Report
from django.views.decorators.cache import cache_page

# Create your views here.
# @cache_page(60 * 15)
def index(request):
    
    filtered = True if request.GET.get('period') != None else False
    if filtered:
        period = request.GET.get('period')
        category  = request.GET.get("category") if request.GET.get("category") != "All" else None
        committee = request.GET.get("committee") if request.GET.get("committee") != "All" else None
        partcipant = request.GET.get("participant") if request.GET.get("participant") != None else None
        reports = Report.objects.filterReports(period,category,committee,partcipant)
    else:
        keyword = request.GET.get('q') if request.GET.get('q') != None else ''
        reports = Report.objects.search(keyword)


    return render(request,'reports/index.html',{'reports':reports})

def reportView(request, pk):
    report = Report.objects.get(pk=pk)
    if not report:
        return HttpResponse("Report not found",status=404)
    recent_reports = Report.objects.all().exclude(pk=report.pk)[:5]
    context = {
        'report': report,
        'recent_reports': recent_reports
    }
    return render(request,'reports/report_details.html',context)