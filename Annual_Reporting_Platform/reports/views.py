

from django.shortcuts import render,redirect,get_object_or_404
from django.http.response import HttpResponse
from .models import Report
from django.views.decorators.cache import cache_page
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)# Create a logger for this module the__name__ variable will be set to the name of the module, which is a common practice for organizing loggers in Python applications.
# Create your views here.
# @cache_page(60 * 15)
def index(request):
    
    filtered = True if request.GET.get('period') != None else False
    if filtered:
        #logger.info("Fetching all approved reports from the database based on filter params")
        period = request.GET.get('period')
        category  = request.GET.get("category") if request.GET.get("category") != "All" else None
        committee = request.GET.get("committee") if request.GET.get("committee") != "All" else None
        partcipant = request.GET.get("participant") if request.GET.get("participant") != None else None
        reports = Report.objects.filterReports(period,category,committee,partcipant).active()
    else:
        #logger.info("Fetching all approved reports from the database based on search")
        keyword = request.GET.get('q') if request.GET.get('q') != None else ''

        reports = Report.objects.search(keyword).active()



    logger.debug(f"Found {reports.count()} reports")
    return render(request,'reports/index.html',{'reports':reports})

def reportView(request, pk):
   # logger.info(f"Fetching report with id {pk} from the database")
    try:

        report = get_object_or_404(Report.objects.active(),pk=pk)


        #logger.debug(f"Found report f{report.title}")
    except Exception as e:
        logger.error(f"Error fetching report with id {pk}: {e}")
        raise

    

    recent_reports = Report.objects.active().exclude(pk=report.pk)[:5]

    context = {
        'report': report,
        'recent_reports': recent_reports
    }
    return render(request,'reports/report_details.html',context)

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
        