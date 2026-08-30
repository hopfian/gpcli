"""Wire-format constants extracted from MyGP 5.31.0 (versionCode 530).

Every value here was derived from the decompiled app (jadx/smali) and
validated against the live API unless noted otherwise.
"""

APP_NAME = "gpcli"

# --- server-visible app identity (must match the Android app) ---
MYGP_APP_VERSION = "5.31.0"  # sent as app_version in login bodies
MYGP_VERSION_CODE = "530"  # embedded in User-Agent
ANDROID_SDK_INT = 34  # emulated Android version

# --- gateways ---
BASE_MYGPAPI = "https://mygp.grameenphone.com/mygpapi"
BASE_APIGW = "https://apigw.grameenphone.com"
BASES: dict[str, str] = {
    "mygpapi": BASE_MYGPAPI,
    "apigw": BASE_APIGW,
}

# --- auth endpoints (legacy gateway) ---
OTP_LOGIN_ENDPOINT = "/v2/otp-login"
SILENT_CODE_ENDPOINT = "/code"
SILENT_VERIFY_ENDPOINT = "/v2/code"
MSISDN_ENDPOINT = "/msisdn"
REFRESH_ENDPOINT_GP = "/v2/oauth/connectid/refresh-token/android"
REFRESH_ENDPOINT_NON_GP = "/v2/refresh-token-all/android"
CONNECTID_TOKEN_ENDPOINT = "/v2/oauth/connectid/get-token/android"
LOGOUT_ENDPOINT = "/logout"
LOGOUT_ALL_ENDPOINT = "/logout-from-all-device"
GUEST_LOGIN_ENDPOINT = "/guest-login"

# --- guest OAuth (Apigee gateway) ---
GUEST_OAUTH_TOKEN_URL = f"{BASE_APIGW}/oauth/v2/token"

# --- account endpoints ---
ME_ENDPOINT = "/me"
BALANCE_ENDPOINT = "/balance"
USAGE_ENDPOINT = "/current-usage"
CUSTOMER_STATUS_ENDPOINT = "/v1/customers/status"

# --- content endpoints ---
CARDS_URL = f"{BASE_APIGW}/mygp/v1/cards"
DISTRICTS_URL = f"{BASE_APIGW}/mygp/v1/districts"
WEATHER_URL = f"{BASE_APIGW}/mygp/v1/weather"
NEWS_ENDPOINT = "/tps/v3/news"

# --- interceptor behavior constants ---
TOKEN_EXPIRY_SKEW = 600  # app refreshes when now > expire_at - 600
REFRESH_MIN_AGE = 600  # app skips refresh if token younger than 600s
ID_PARAM_SKIP_MARKERS = ("v2/sbcontents/search", "v2/sbcontents/get-content-by-id")


def build_user_agent(language: str = "en") -> str:
    """UserAgentInterceptor -> Utils.M(): `Android/{sdk} MyGP/{code} ({lang})`."""
    return f"Android/{ANDROID_SDK_INT} MyGP/{MYGP_VERSION_CODE} ({language})"
