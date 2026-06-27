from eco.eco_1c_utils import try_bind_eco_1c_user


class Eco1cUserMiddleware:
    """
    Для запросов к /eco/ подставляет пользователя из сессии 1С или ?uin=
    (без auth.login), чтобы @login_required и request.user работали как обычно.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = try_bind_eco_1c_user(request)
        if user is not None:
            request.user = user
        return self.get_response(request)
