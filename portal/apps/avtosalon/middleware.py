# -*- coding: utf-8 -*-
"""Middleware для сводки продавца: подставляет пользователя из сессии 1С или ?uin=."""
from avtosalon.seller_brief_1c_utils import (
    get_seller_brief_1c_user_from_session,
    is_seller_brief_1c_session,
    is_seller_brief_request,
    try_bind_seller_brief_1c_user,
)


class SellerBrief1cUserMiddleware:
    """
    Для запросов к сводке продавца (/cars/.../seller_brief/...) подставляет пользователя
    из изолированной сессии 1С или ?uin= (без django.contrib.auth.login), чтобы @login_required
    и проверки request.user работали как обычно, не сбрасывая активную сессию портала в браузере.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = try_bind_seller_brief_1c_user(request)
        if user is not None:
            request.user = user
        elif is_seller_brief_1c_session(request) and is_seller_brief_request(request):
            u = get_seller_brief_1c_user_from_session(request)
            if u is not None:
                request.user = u
        return self.get_response(request)
