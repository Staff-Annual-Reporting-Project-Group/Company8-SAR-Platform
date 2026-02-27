from django.shortcuts import render
from django.http.response import HttpResponse
from .models import Report

# Create your views here.
def index(request):
    keyword = request.GET.get('q') if request.GET.get('q') != None else ''
    reports = Report.objects.search(keyword)
    return render(request,'reports/index.html',{'reports':reports})