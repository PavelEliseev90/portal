from eco.eco_1c_utils import is_eco_1c_session, is_eco_request
from estimations.estimation_1c_utils import is_estimation_1c_session, is_estimation_request


def estimation_1c_layout(request):
    estimation_compact = (
        is_estimation_1c_session(request) and is_estimation_request(request)
    )
    eco_compact = is_eco_1c_session(request) and is_eco_request(request)
    compact = estimation_compact or eco_compact
    menu_collapsed = compact or request.COOKIES.get('menu') == '1'
    return {
        'estimation_1c_compact_layout': compact,
        'menu_collapsed': menu_collapsed,
    }
