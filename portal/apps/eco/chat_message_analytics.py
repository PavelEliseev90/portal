"""Поиск по сообщениям чатов интерактивных оценок."""
from __future__ import annotations

import html
import re
from typing import Iterable, List, Optional

from django.contrib.auth import get_user_model
from django.db.models import Q

from analytics.models import TradeInFunnel
from chats.models import ChatMessage
from register.models import RegInteractivOcenkaRLK

User = get_user_model()

RESULT_LIMIT = 300


def parse_phrases(raw: str) -> List[str]:
    """Фразы из textarea: по строкам и через ; / |."""
    if not raw:
        return []
    phrases = []
    for line in str(raw).replace('|', '\n').replace(';', '\n').splitlines():
        part = line.strip()
        if part:
            phrases.append(part)
    # уникальные с сохранением порядка
    seen = set()
    out = []
    for p in phrases:
        key = p.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out[:20]


def parse_user_ids(raw_list) -> List[int]:
    ids = []
    if not raw_list:
        return ids
    if isinstance(raw_list, str):
        raw_list = [raw_list]
    for item in raw_list:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _user_label(user) -> str:
    if user is None:
        return '—'
    try:
        eco = (user.profiles.eco_name or '').strip()
    except Exception:
        eco = ''
    if eco:
        return eco
    name = f'{user.last_name or ""} {user.first_name or ""}'.strip()
    return name or user.username or f'#{user.pk}'


def highlight_phrases(text: str, phrases: Iterable[str]) -> str:
    escaped = html.escape(text or '')
    for phrase in phrases:
        if not phrase:
            continue
        pattern = re.compile(re.escape(html.escape(phrase)), re.IGNORECASE)
        escaped = pattern.sub(
            lambda m: f'<mark class="chat-hit">{m.group(0)}</mark>',
            escaped,
        )
    return escaped.replace('\n', '<br>')


def _author_base_qs():
    return (
        User.objects
        .filter(is_active=True)
        .filter(
            Q(profiles__eco=True)
            | Q(profiles__eco_visible=True)
            | Q(profiles__eco_name__gt='')
        )
        .select_related('profiles')
        .distinct()
    )


def _author_dict(user) -> dict:
    return {
        'id': user.pk,
        'label': _user_label(user),
        'username': user.username or '',
        'email': (user.email or '').strip(),
    }


def author_choices():
    """Полный список (legacy). Для UI не используем — только search_authors."""
    qs = _author_base_qs().order_by('last_name', 'first_name', 'username')[:800]
    return [_author_dict(u) for u in qs]


def authors_by_ids(user_ids: Iterable[int]) -> List[dict]:
    """Выбранные авторы для бейджей после отправки формы."""
    ids = []
    for i in user_ids or []:
        try:
            ids.append(int(i))
        except (TypeError, ValueError):
            continue
    if not ids:
        return []
    qs = User.objects.filter(pk__in=ids).select_related('profiles')
    by_id = {u.pk: _author_dict(u) for u in qs}
    return [by_id[i] for i in ids if i in by_id]


def search_authors(query: str, limit: int = 20) -> List[dict]:
    """
    Живой поиск авторов по ФИО / eco_name / логину / email.
    Пустой query → пустой список (без предзагрузки).
    """
    q = (query or '').strip()
    if len(q) < 2:
        return []
    try:
        limit = max(1, min(int(limit or 20), 40))
    except (TypeError, ValueError):
        limit = 20

    parts = [p for p in q.replace(',', ' ').split() if p]
    qs = _author_base_qs()
    if len(parts) >= 2:
        name_q = Q()
        for part in parts[:4]:
            name_q &= (
                Q(profiles__eco_name__icontains=part)
                | Q(first_name__icontains=part)
                | Q(last_name__icontains=part)
                | Q(username__icontains=part)
                | Q(email__icontains=part)
            )
        qs = qs.filter(name_q)
    else:
        part = parts[0]
        qs = qs.filter(
            Q(profiles__eco_name__icontains=part)
            | Q(username__icontains=part)
            | Q(email__icontains=part)
            | Q(first_name__icontains=part)
            | Q(last_name__icontains=part)
        )

    qs = qs.order_by('last_name', 'first_name', 'username')[:limit]
    return [_author_dict(u) for u in qs]


def search_chat_messages(date_start, date_end, phrases=None, user_ids=None, limit=RESULT_LIMIT) -> dict:
    phrases = phrases or []
    user_ids = user_ids or []

    qs = (
        ChatMessage.objects
        .filter(date__gte=date_start, date__lte=date_end)
        .filter(Q(chat__slug__startswith='rlk_') | Q(chat__rlk_id__gt=0))
        .select_related('user', 'user__profiles', 'chat')
        .order_by('-date')
    )

    if user_ids:
        qs = qs.filter(user_id__in=user_ids)

    if phrases:
        phrase_q = Q()
        for phrase in phrases:
            phrase_q |= Q(content__icontains=phrase)
        qs = qs.filter(phrase_q)

    total_matched = qs.count()
    messages = list(qs[:limit])

    rlk_ids = set()
    for msg in messages:
        chat = msg.chat
        if chat is None:
            continue
        rid = chat.rlk_id or 0
        if not rid and chat.slug and chat.slug.startswith('rlk_'):
            try:
                rid = int(chat.slug.replace('rlk_', '', 1))
            except (TypeError, ValueError):
                rid = 0
        if not rid and chat.name:
            try:
                rid = int(chat.name)
            except (TypeError, ValueError):
                rid = 0
        msg._rlk_id = rid or None
        if rid:
            rlk_ids.add(rid)

    funnel_map = {}
    if rlk_ids:
        funnel_map = {
            f.rlk_id: f
            for f in TradeInFunnel.objects.filter(rlk_id__in=rlk_ids).only(
                'rlk_id', 'rlk_number', 'mark_name', 'model_name', 'run',
                'unit_name', 'city_name', 'brand', 'vin', 'year',
            )
        }

    rlk_extra = {}
    missing = [rid for rid in rlk_ids if rid not in funnel_map]
    if missing:
        for row in (
            RegInteractivOcenkaRLK.objects
            .filter(rlk_id__in=missing)
            .select_related('unit', 'filial', 'rlk', 'estimation', 'estimation__page_salon')
        ):
            rlk_extra[row.rlk_id] = row

    # филиал для тех, у кого есть funnel — добрать из RLK при необходимости
    filial_map = {}
    need_filial = [rid for rid in rlk_ids if rid]
    if need_filial:
        for row in (
            RegInteractivOcenkaRLK.objects
            .filter(rlk_id__in=need_filial)
            .select_related('filial', 'unit')
        ):
            filial_map[row.rlk_id] = {
                'filial': getattr(row.filial, 'name', '') or '',
                'unit': getattr(row.unit, 'name', '') or '',
            }

    rows = []
    for msg in messages:
        rlk_id = getattr(msg, '_rlk_id', None)
        funnel = funnel_map.get(rlk_id) if rlk_id else None
        extra = rlk_extra.get(rlk_id) if rlk_id else None
        filial_info = filial_map.get(rlk_id) or {}

        mark = ''
        model = ''
        run = 0
        unit_name = ''
        filial_name = filial_info.get('filial') or ''
        rlk_number = ''
        year = 0

        if funnel:
            mark = funnel.mark_name or ''
            model = funnel.model_name or ''
            run = funnel.run or 0
            unit_name = funnel.unit_name or filial_info.get('unit') or ''
            rlk_number = funnel.rlk_number or ''
            year = funnel.year or 0
            if not filial_name and funnel.city_name:
                filial_name = funnel.city_name
        elif extra:
            est = extra.estimation
            if est:
                mark = est.mark_name or ''
                model = est.model_name or ''
                year = est.year or 0
                if est.page_salon_id:
                    run = getattr(est.page_salon, 'run', 0) or 0
            unit_name = getattr(extra.unit, 'name', '') or ''
            filial_name = getattr(extra.filial, 'name', '') or filial_name
            rlk_number = getattr(extra.rlk, 'nomer', '') or ''

        content = msg.content or ''
        rows.append({
            'id': msg.pk,
            'date': msg.date,
            'content': content,
            'content_html': highlight_phrases(content, phrases),
            'author': _user_label(msg.user),
            'author_id': msg.user_id,
            'rlk_id': rlk_id,
            'rlk_number': rlk_number,
            'mark': mark,
            'model': model,
            'year': year,
            'run': run,
            'unit_name': unit_name or '—',
            'filial_name': filial_name or '—',
            'eco_url': f'/eco/{rlk_id}/' if rlk_id else '',
        })

    return {
        'rows': rows,
        'total_matched': total_matched,
        'returned': len(rows),
        'limited': total_matched > len(rows),
        'limit': limit,
        'phrases': phrases,
    }
