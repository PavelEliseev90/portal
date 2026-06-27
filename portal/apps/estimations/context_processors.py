from estimations.estimation_1c_utils import is_estimation_1c_session, is_estimation_request


def estimation_1c_layout(request):
    compact = is_estimation_1c_session(request) and is_estimation_request(request)
    menu_collapsed = compact or request.COOKIES.get('menu') == '1'
    return {
        'estimation_1c_compact_layout': compact,
        'menu_collapsed': menu_collapsed,
    }
