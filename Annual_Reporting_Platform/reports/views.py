

from django.shortcuts import render,redirect
from django.http.response import HttpResponse
from .models import Report
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Create your views here.
# @cache_page(60 * 15)
def index(request):
    
    filtered = True if request.GET.get('period') != None else False
    if filtered:
        period = request.GET.get('period')
        category  = request.GET.get("category") if request.GET.get("category") != "All" else None
        committee = request.GET.get("committee") if request.GET.get("committee") != "All" else None
        partcipant = request.GET.get("participant") if request.GET.get("participant") != None else None
        reports = Report.all_objects.filterReports(period,category,committee,partcipant)
    else:
        keyword = request.GET.get('q') if request.GET.get('q') != None else ''
        reports = Report.all_objects.search(keyword)


    return render(request,'reports/index.html',{'reports':reports})

def reportView(request, pk):
    report = Report.all_objects.get(pk=pk)
    if not report:
        return HttpResponse("Report not found",status=404)
    recent_reports = Report.all_objects.all().exclude(pk=report.pk)[:5]
    context = {
        'report': report,
        'recent_reports': recent_reports
    }
    return render(request,'reports/report_details.html',context)

@login_required
def deleteReport(request,pk):
    report = Report.objects.get(pk=pk)
    if not report:
       messages.error(request, 'Report does not exists')
       return  redirect('users:profile')
    else:
        if request.user == report.user:
            report.delete()
            messages.success(request,"Report Deleted Successfully")
            return redirect('users:profile')
        else:
            messages.error(request, 'User was not the owner of the report')
            
    return redirect('users:profile')
        