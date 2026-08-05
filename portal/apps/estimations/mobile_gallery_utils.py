from django.core import signing

ESTIMATION_UPLOAD_SALT = 'estimation-mobile-upload-v1'
ESTIMATION_UPLOAD_MAX_AGE = 60 * 60 * 24  # 24 часа

MOBILE_INBOX_TYPE_FILE = 'mobile_inbox'


def make_estimation_upload_token(estimation_id):
    signer = signing.TimestampSigner(salt=ESTIMATION_UPLOAD_SALT)
    return signer.sign(str(int(estimation_id)))


def verify_estimation_upload_token(token):
    if not token:
        return None
    signer = signing.TimestampSigner(salt=ESTIMATION_UPLOAD_SALT)
    try:
        value = signer.unsign(token, max_age=ESTIMATION_UPLOAD_MAX_AGE)
        return int(value)
    except (signing.BadSignature, signing.SignatureExpired, ValueError, TypeError):
        return None


def build_mobile_upload_url(request, estimation_id):
    token = make_estimation_upload_token(estimation_id)
    return request.build_absolute_uri(
        f'/estimations/mobile-gallery/{token}/'
    )
