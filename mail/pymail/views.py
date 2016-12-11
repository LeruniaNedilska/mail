from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from forms import RegistrationForm
from django.contrib.auth.decorators import login_required
import datetime as dt


def signin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect("/")
        else:
            error_message = "No such user registered yet :("
            return render(request, 'sign_in.html', {'error_message': error_message})
    else:
        return render(request, 'sign_in.html')


@csrf_protect
def signup(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('Yep')
        else:
            return render(request, 'sign_in.html', {'errors': form.errors})
    else:
        return render(request, 'sign_in.html')


@login_required(login_url='/signin')
def signout(request):
    logout(request)
    return HttpResponseRedirect('/signin')


@login_required(login_url='/signin')
def inbox(request):
    return render(request, 'inbox.html', {'user': request.user})


@login_required(login_url='/signin')
def sent(request):
    return render(request, 'sent.html', {'user': request.user})


@login_required(login_url='/signin')
def important(request):
    return render(request, 'important.html', {'user': request.user})


@login_required(login_url='/signin')
def trash(request):
    return render(request, 'trash.html', {'user': request.user})


@login_required(login_url='/signin')
def spam(request):
    return render(request, 'spam.html', {'user': request.user})


@login_required(login_url='/signin')
def new(request):
    return render(request, 'new.html', {'user': request.user})


@login_required(login_url='/signin')
def received(request):
    return render(request, 'received.html', {'user': request.user, 'dt': dt.datetime.now()})


def start(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/inbox')
    else:
        return HttpResponseRedirect('/signin')
