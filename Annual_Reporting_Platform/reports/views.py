from django.shortcuts import render
from django.http.response import HttpResponse
from .models import Report

# Create your views here.
def index(request):
    reports = Report.objects.all()
    return render(request,'reports/index.html',{'reports':reports})