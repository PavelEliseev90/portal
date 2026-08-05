from django.core import signing

ESTIMATION_UPLOAD_SALT = 'estimation-mobile-upload-v1'
ESTIMATION_UPLOAD_MAX_AGE = 60 * 60 * 24  # 24 часа

MOBILE_INBOX_TYPE_FILE = 'mobile_inbox'
MOBILE_GALLERY_PATH_PREFIX = '/estimations/mobile-gallery/'


def is_mobile_gallery_path(path):
    return (path or '').startswith(MOBILE_GALLERY_PATH_PREFIX)


def is_mobile_gallery_next(next_url):
    """next из /login/?next=... — путь или абсолютный URL страницы загрузки фото."""
    if not next_url:
        return False
    path = next_url
    if '://' in next_url:
        from urllib.parse import urlparse
        path = urlparse(next_url).path or ''
    return is_mobile_gallery_path(path)


def make_estimation_upload_token(estimation_id):
    signer = signing.TimestampSigner(salt=ESTIMATION_UPLOAD_SALT)
    return signer.sign(str(int(estimation_id)))


def verify_estimation_upload_token(token):
    if not token:
        return None
    signer = signing.TimestampSigner(salt=ESTIMATION_UPLOAD_SALT)
    try:
        value = signer.unsign(token, max_age=ESTIMATION_UPLOAD_MAX_AGE)
    except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
        return None
    return int(value)


def build_mobile_upload_url(request, estimation_id):
    token = make_estimation_upload_token(estimation_id)
    return request.build_absolute_uri(
        f'/estimations/mobile-gallery/{token}/'
    )
