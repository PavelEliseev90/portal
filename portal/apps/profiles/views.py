from django.shortcuts import render
from django.core.paginator import Paginator
import json
from profiles.models import Profiles
from fuzzywuzzy import fuzz
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
import datetime as DT


def profiles_edit(request):
    if request.user.is_authenticated:
        if request.method == "GET":
            params = {
                'type'  : 'profiles',
                'user'  : request.user
            }
            return render(request, "profiles/profiles_edit.html", {'params': params})
        else:
            user     = request.user
            profiles = user.profiles
            if 'update_logo' in request.POST:
                file_list = request.FILES.getlist('file')
                if len(file_list) > 0:
                    profiles.image = file_list[0]
            if 'update_info' in request.POST:
                if len(request.POST['birth_date']) > 0:
                    birth_date = DT.datetime.strptime(request.POST['birth_date'],'%Y-%m-%d')
                    profiles.birth_date = birth_date

            profiles.save()
            return HttpResponseRedirect(request.build_absolute_uri())  
    else:
        return HttpResponseRedirect('/login')