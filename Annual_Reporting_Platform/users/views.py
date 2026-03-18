from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required

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
    return render(request,'reports/index')

@login_required
def profile_view(request):
    return render(request,'users/profile.html')

