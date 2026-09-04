from django.shortcuts import render
from django.core.paginator import Paginator
import json
from profiles.models import Profiles
from fuzzywuzzy import fuzz
from django.http import Http404, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
import datetime as DT
from django.contrib import messages


def profiles_edit(request):
    if request.user.is_authenticated:
        telegram_bot_username = ''
        telegram_bot_url = ''
        try:
            from avtosalon.deal_calc_telegram import get_bot_username
            telegram_bot_username = get_bot_username() or ''
            if telegram_bot_username:
                telegram_bot_url = 'https://t.me/{}'.format(telegram_bot_username)
        except Exception:
            pass

        if request.method == "GET":
            params = {
                'type': 'profiles',
                'user': request.user,
                'telegram_bot_username': telegram_bot_username,
                'telegram_bot_url': telegram_bot_url,
            }
            return render(request, "profiles/profiles_edit.html", {'params': params})
        else:
            user = request.user
            profiles = user.profiles
            if 'update_logo' in request.POST:
                file_list = request.FILES.getlist('file')
                if len(file_list) > 0:
                    profiles.image = file_list[0]
            if 'update_info' in request.POST:
                if len(request.POST.get('birth_date') or '') > 0:
                    birth_date = DT.datetime.strptime(request.POST['birth_date'], '%Y-%m-%d')
                    profiles.birth_date = birth_date

                if (
                    profiles.price_car_new_director
                    or profiles.price_car_new_all
                ):
                    from avtosalon.deal_calc_telegram import normalize_telegram_chat_id
                    raw_chat = request.POST.get('telegram_chat_id', '')
                    chat_id = normalize_telegram_chat_id(raw_chat)
                    if (raw_chat or '').strip() and not chat_id:
                        messages.error(
                            request,
                            'Некорректный Telegram chat ID. Укажите числовой Id из @userinfobot.',
                        )
                    else:
                        profiles.telegram_chat_id = chat_id

                    profiles.telegram_notify_pending = (
                        'telegram_notify_pending' in request.POST
                    )
                    profiles.telegram_notify_auto_approved = (
                        'telegram_notify_auto_approved' in request.POST
                    )
                    profiles.telegram_notify_results = (
                        'telegram_notify_results' in request.POST
                    )
            if 'eco_toast' in request.POST:
                profiles.eco_toast = True
            else:
                profiles.eco_toast = False

            profiles.save()
            return HttpResponseRedirect(request.build_absolute_uri())
    else:
        return HttpResponseRedirect('/login')
