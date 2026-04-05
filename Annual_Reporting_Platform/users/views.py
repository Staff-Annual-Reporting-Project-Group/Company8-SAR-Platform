from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from reports.models import Report,Category

# Create your views here.
def loginPage(request):
    if request.user.is_authenticated:
        redirect('reports:index')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        #print("Tried with " + username)
        user = User.objects.filter(Q(username=username) | Q(email = username)).first()
        if not user:
            messages.error(request,"User does not exist")
            return redirect('users:login')
        username = user.username
        user = authenticate(request, username =username, password=password)
        if user is not None:
            login(request,user)
            return redirect('reports:index')
        else:
            messages.error(request, 'Username OR password does not exist')

    return render(request,'users/login.html',{})


def logout_view(request):
    logout(request)
    return redirect('reports:index')

@login_required
def profile_view(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    user = request.user
    reports = Report.objects.all().filter(user = user)
    if q != '':
        reports = reports.filter(Q(title__icontains=q) |
                    Q(description__icontains=q)
                    )
    # reports = user.reports.all()
    context = {'reports':reports}
    return render(request,'users/profile.html',context)

@login_required
def create_report_view(request):
    # title
    # description
    # participants
    # category
    # committees
    # image

    if request.method == "POST":
        return
    categories = Category.objects.all()
    context = {
        'title' : "Create a New Report",
        'categories': categories
    }
    return render(request,"users/create_report.html",context)