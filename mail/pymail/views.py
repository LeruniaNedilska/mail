from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from pymail.forms import RegistrationForm
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from pymail.mongo import DB
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import resolve
from django.contrib.auth.models import User

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
            db.send_registration_message(request.POST['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return HttpResponseRedirect('/signin')
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
    #print(db.db.eval("""Object.bsonsize(db.mail.find())"""))
    #return render(request, 'test.html', {'context': db.stats("2016-12")})
    switcher = {
        'inbox': 'inbox.html',
        'sent': 'sent.html',
        'important': "important.html",
        'trash': "trash.html",
        'spam': "spam.html",
        'search': "search.html"
    }
    current_url = resolve(request.path_info).url_name
    search_amount = 0
    if current_url == 'important':
        message_list, msg = db.find_important_messages(request.user.username)
        print(msg)
        important_messages = len(message_list)
    elif current_url == 'search':
        if request.POST['type'] == 'important':
            message_list = db.find_important_message_by_text(request.user.username, request.POST['phrase'])
        else:
            message_list = db.find_message_by_text(request.user.username, request.POST['type'], request.POST['phrase'])
        important_messages = db.important_messages_amount(request.user.username)
        search_amount = len(message_list)
    else:
        message_list, msg = db.get_category(request.user.username, current_url)
        print(msg)
        important_messages = db.important_messages_amount(request.user.username)
    new_messages = db.new_message_amount(request.user.username)
    other_messages = db.message_amount(request.user.username)
    page = request.GET.get('page', 1)

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
                                                       "important": important_messages,
                                                       "category": current_url,
                                                       "amount": search_amount})


@login_required(login_url='/signin')
def new(request):
    important_messages = db.important_messages_amount(request.user.username)
    new_messages = db.new_message_amount(request.user.username)
    other_messages = db.message_amount(request.user.username)
    to = request.POST.get('to', None)
    subject = request.POST.get('subject', None)
    return render(request, 'new.html', {'user': request.user, "new": new_messages,
                                        "sent": other_messages['sentNumber'],
                                        "spam": other_messages['spamNumber'],
                                        "trash": other_messages['trashNumber'],
                                        "important": important_messages,
                                        "to": to,
                                        "subject": subject})


@csrf_protect
def send_new_message(request):
    to = []
    splits = request.POST['to'].split(",")
    for s in splits:
        to.append(s.split('@')[0])
    db.add_message(request.user.username, to, request.POST['subject'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   request.POST['text'], "sent", request.user.username)
    for user in to:
        db.add_message(request.user.username, to, request.POST['subject'],
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request.POST['text'], "inbox", user, read=False)
    return HttpResponseRedirect('/sent')


@login_required(login_url='/signin')
def message(request, category, message_id):
    db.mark_message_read(request.user.username, message_id, True)
    important_messages = db.important_messages_amount(request.user.username)
    new_messages = db.new_message_amount(request.user.username)
    other_messages = db.message_amount(request.user.username)
    if category != 'important' and category != 'search':
        mess = db.find_message_by_id(request.user.username, category, message_id)
    else:
        mess = db.find_message_by_id(request.user.username, db.find_message_category(request.user.username, message_id),
                                     message_id)
    return render(request, 'received_'+category+'.html', {"user": request.user, "new": new_messages,
                                                          "sent": other_messages['sentNumber'],
                                                          "spam": other_messages['spamNumber'],
                                                          "trash": other_messages['trashNumber'],
                                                          "important": important_messages,
                                                          "from": mess['from'],
                                                          "to": mess['to'],
                                                          "subject": mess['subject'],
                                                          "text": mess['text'],
                                                          "date": mess['date'],
                                                          "id": mess['_id'],
                                                          "category": category})


def start(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/inbox')
    else:
        return HttpResponseRedirect('/signin')


def choose_return(request):
    if request.POST['noreturn'] == 'no':
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
        return HttpResponseRedirect('/inbox')


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
    return choose_return(request)


def delete(request):
    for item in request.POST.getlist('mail_list'):
        db.remove_message(request.POST['previous'], request.user.username, item)
    return choose_return(request)


def move_to_spam(request):
    for item in request.POST.getlist('mail_list'):
        db.move_message(request.user.username, request.POST['previous'], item, "spam")
    return choose_return(request)


def mark_as_important(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_important(request.user.username, item, True, request.POST['previous'])
    return choose_return(request)


def mark_as_not_important(request):
    for item in request.POST.getlist('mail_list'):
        db.mark_message_important(request.user.username, item, False)
    return choose_return(request)


def swap_back(request):
    for item in request.POST.getlist('mail_list'):
        db.move_message(request.user.username, request.POST['previous'], item)
    return choose_return(request)


def delete_users(request):
    for item in request.POST.getlist('mail_list'):
        User.objects.filter(username=item).delete()
        db.remove_user(item)
    return HttpResponseRedirect('/inbox')


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
        'swap': swap_back,
        'reply': new,
        'delete_users': delete_users
    }
    func = switcher.get(request.POST['action'])
    return func(request)


@login_required(login_url='/signin')
def stats(request, days):
    today = datetime.now()
    stat = db.stats(today.strftime("%Y-%m-%d"))
    all = []
    all.append(stat)
    for i in range(1, int(days)):
        next_stats = db.stats((today - timedelta(days=i)).strftime("%Y-%m-%d"))
        all.append(next_stats)
    result = {}
    for user in db.mail.find():
        memory = db.memory_usage(user['_id'])
        result[user['_id']] = {}
        result[user['_id']]['inbox'] = sum(item[user['_id']]['inbox'] for item in all)
        result[user['_id']]['sent'] = sum(item[user['_id']]['sent'] for item in all)
        result[user['_id']]['spam'] = sum(item[user['_id']]['spam'] for item in all)
    important_messages = db.important_messages_amount(request.user.username)
    new_messages = db.new_message_amount(request.user.username)
    other_messages = db.message_amount(request.user.username)
    return render(request, "test.html", {'context': result,
                                         "user": request.user, "new": new_messages,
                                         "sent": other_messages['sentNumber'],
                                         "spam": other_messages['spamNumber'],
                                         "trash": other_messages['trashNumber'],
                                         "important": important_messages,
                                         })


@login_required(login_url='/signin')
def memory_usage(request):
    result ={}
    for user in db.mail.find():
        memory = db.memory_usage(user['_id'])
        result[user['_id']] = {}
        result[user['_id']]['dbhits'] = memory['dbhits']
        result[user['_id']]['cachehits'] = memory['cachehits']
    return render(request, "memory.html", {'context': result})
