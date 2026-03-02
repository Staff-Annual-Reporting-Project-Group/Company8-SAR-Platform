from django.shortcuts import render
from django.http.response import HttpResponse
from .models import Report

# Create your views here.
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