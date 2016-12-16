from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from pymail.forms import RegistrationForm
from django.contrib.auth.decorators import login_required
import datetime as dt
from pymail.mongo import DB
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import resolve

db = DB()


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
            db.add_user(request.POST['username'])
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
def template(request):
    switcher = {
        'inbox': 'inbox.html',
        'sent': 'sent.html',
        'important': "important.html",
        'trash': "trash.html",
        'spam': "spam.html",
    }
    current_url = resolve(request.path_info).url_name
    if current_url != 'important':
        message_list = db.find_users_messages(request.user.username, current_url)
        important_messages = db.important_messages_amount(request.user.username)
    else:
        message_list = db.find_important_messages(request.user.username)
        important_messages = len(message_list)
    new_messages = db.new_message_amount(request.user.username)
    other_messages = db.message_amount(request.user.username)
    page = request.GET.get('page')

    paginator = Paginator(message_list, 25)
    try:
        messages = paginator.page(page)
    except PageNotAnInteger:
        messages = paginator.page(1)
    except EmptyPage:
        messages = paginator.page(paginator.num_pages)

    return render(request, switcher.get(current_url), {'user': request.user, "messages": messages, "new": new_messages,
                                                       "sent": other_messages['sentNumber'],
                                                       "spam": other_messages['spamNumber'],
                                                       "trash": other_messages['trashNumber'],
                                                       "important": important_messages})


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


def set_as_read(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_read(request.user.username, item, True)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def set_as_not_read(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_read(request.user.username, item, False)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def move_to_trash(request):
    for item in request.POST.getlist('mail_list'):
        db.move_message(request.user.username, request.POST['previous'], item, "trash")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def delete(request):
    for item in request.POST.getlist('mail_list'):
        db.remove_message(request.POST['previous'], request.user.username, item)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def move_to_spam(request):
    for item in request.POST.getlist('mail_list'):
        db.move_message(request.user.username, request.POST['previous'], item, "spam")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def mark_as_important(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_important(request.user.username, item, True, request.POST['previous'])
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def mark_as_not_important(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_important(request.user.username, item, False)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def swap_back(request):
    for item in request.POST.getlist('mail_list'):
        db.move_message(request.user.username, request.POST['previous'], item)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@csrf_protect
def handler(request):
    switcher = {
        'visible': set_as_read,
        'unvisible': set_as_not_read,
        'delete': move_to_trash,
        'delete_forever': delete,
        'spam': move_to_spam,
        'important': mark_as_important,
        'not_important': mark_as_not_important,
        'swap': swap_back
    }
    func = switcher.get(request.POST['action'])
    return func(request)
