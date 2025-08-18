from django.shortcuts import render
import requests
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
import json

#Настройки параметров доступа
server      = 'http://a01srv1cka/softonit/hs/portal/'
time_out    = 5

def tasks_user_desctop(user):
    try:
        url_search = ''
        if len(str(user)) > 0:
            url_search = '?user_login=' + str(user)
        answer      = requests.get(server + 'desctop' + url_search, timeout = time_out)
        json_text   = json.loads(answer.text)
    except:
        json_text = {}
    return json_text

def task_list(request):

    if request.user.is_authenticated:
        url         = request.build_absolute_uri()
       
        url_search  = ''
        if url.find('?') > -1:
            url_search = "?" + url.split('?')[1]
        if not request.user.is_superuser:
            if len(url_search) == 0:
                url_search = '?user_login=' + str(request.user)
        #url_search = '?user_login=' + str(request.user)
        answer      = requests.get(server + 'tasks' + url_search, timeout = time_out)
        json_text   = json.loads(answer.text)
        filtr       = dict()
        
        filtr_count = 0

        for key in request.GET.keys():
            value = request.GET.get(key) 
            if len(value) > 0:
                if key == 'page':
                    filtr[key] = int(value)
                else: 
                    filtr[key] = value
                    filtr_count = filtr_count + 1
            
        params = {
            'type'          : 'help',
            'test'          : '1',
            'filtr'         : filtr,
            'filtr_count'   : filtr_count,
            'answer'        : json_text
        }
        return render(request, "help_desk/task_list.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login') 


def task(request, id):

    if request.user.is_authenticated:
        answer      = requests.get(server + 'task/' + id, timeout = time_out)
        json_text   = ''
        if answer.status_code == 200:
            if len(answer.text) > 3:
                json_text = json.loads(answer.text)
        params = {
            'type'      : 'help',
            'test'      : '1',
            'answer'    : json_text
        }
        return render(request, "help_desk/task.html", {'params': params})    
    else:
        return HttpResponseRedirect('/login') 