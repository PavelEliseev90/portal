import threading


_thread_local = threading.local()


class LoggedInUser(object):
  """
  Пользователь текущего HTTP-запроса.

  Данные хранятся в threading.local (не в процессном синглтоне),
  иначе при параллельных запросах в одном воркере в ChangeLog
  попадала чужая учётка.
  """

  def set_data(self, request):
    _thread_local.request = id(request)
    if getattr(request, 'user', None) is not None and request.user.is_authenticated:
      _thread_local.user = request.user
      _thread_local.address = request.META.get('REMOTE_ADDR')
    else:
      _thread_local.user = None
      _thread_local.address = None

  def clear(self):
    _thread_local.request = None
    _thread_local.user = None
    _thread_local.address = None

  @property
  def request(self):
    return getattr(_thread_local, 'request', None)

  @property
  def current_user(self):
    return getattr(_thread_local, 'user', None)

  @property
  def address(self):
    return getattr(_thread_local, 'address', None)

  @property
  def have_user(self):
    return self.current_user is not None


class LoggedInUserMiddleware(object):
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    """
    Инициализирует LoggedInUser для текущего потока и очищает после ответа.
    """
    logged_in_user = LoggedInUser()
    logged_in_user.set_data(request)
    try:
      return self.get_response(request)
    finally:
      logged_in_user.clear()


def _should_log_pageview(request):
  """Не логируем статику, медиа и сам дашборд логов."""
  path = request.path
  if path.startswith(('/static/', '/media/', '/media_dop/', '/favicon', '/__debug__')):
    return False
  if path.startswith('/changelog/pageview-dashboard') or path.startswith('/admin/jsi18n'):
    return False
  if path.startswith('/api/'):
    return False
  if path.startswith('/cars/deal/rlk-chat/poll/'):
    return False
  if path.startswith('/cars/deal/rlk-chat/send/'):
    return False
  return True


class PageViewLogMiddleware(object):
  """Пишет в PageViewLog каждый запрос (GET/POST) для авторизованных и анонимов."""
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    response = self.get_response(request)
    if not _should_log_pageview(request):
      return response
    try:
      from changelog.models import PageViewLog
      path = request.path[:500]
      path_full = request.get_full_path()[:1024]
      user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
      session_key = (request.session.session_key or '')[:40] if getattr(request, 'session', None) else ''
      ip = request.META.get('REMOTE_ADDR')
      if ip and len(ip) > 45:
        ip = None
      ua_raw = (request.META.get('HTTP_USER_AGENT') or '')[:512]
      device_type = ''
      if getattr(request, 'user_agent', None):
        ua = request.user_agent
        if getattr(ua, 'is_bot', False):
          device_type = 'bot'
        elif getattr(ua, 'is_mobile', False) and not getattr(ua, 'is_tablet', False):
          device_type = 'mobile'
        elif getattr(ua, 'is_tablet', False):
          device_type = 'tablet'
        elif getattr(ua, 'is_pc', False):
          device_type = 'pc'
      if not device_type:
        device_type = 'unknown'
      PageViewLog.objects.create(
        user=user,
        session_key=session_key,
        path=path,
        path_full=path_full,
        method=request.method[:10] or 'GET',
        status_code=response.status_code if hasattr(response, 'status_code') else None,
        ip=ip,
        device_type=device_type,
        user_agent=ua_raw,
      )
    except Exception:
      pass
    return response
