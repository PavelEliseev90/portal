from estimations.estimation_1c_utils import (
    ESTIMATION_1C_ENTRY_PREFIX,
    ESTIMATION_PATH,
    get_estimation_1c_user_from_session,
    is_estimation_1c_session,
)


class Estimation1cUserMiddleware:
    """
    Для запросов к /estimations/ подставляет пользователя из сессии 1С
    (без auth.login), чтобы существующие проверки request.user работали как обычно.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_estimation_1c_session(request):
            path = request.path_info or ''
            if path.startswith(ESTIMATION_PATH) and not path.startswith(ESTIMATION_1C_ENTRY_PREFIX):
                user = get_estimation_1c_user_from_session(request)
                if user is not None:
                    request.user = user
        return self.get_response(request)
