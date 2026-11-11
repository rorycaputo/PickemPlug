import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
import requests
from lxml import etree, html
import apis
import storage

SAVED_PAGE_KEY = 'cache/pickem.html'
AUTH_VERSION = 1
# Cookies that carry the CBS login; the rest of the browser's cookies are consent/analytics.
# Live testing showed the pool page needs `pid`; auth_session/auth_state alone get redirected to /join.
AUTH_COOKIE_NAMES = ('auth_session', 'auth_state', 'pid')
AUTH_COOKIE_FIELDS = ('name', 'value', 'domain', 'path', 'secure', 'httpOnly', 'expiry')
POOL_URL = 'https://picks.cbssports.com/football/pickem/pools/kbxw63b2geztqnjuha2ds===?entryId=ivxhi4tzhizdcnbrgm2tinbs'
LOGGED_OUT_PATHS = ('/login', '/join')
REQUEST_TIMEOUT_SECONDS = 30
# pickem_html_url = 'https://picks.cbssports.com/football/pickem/pools/kbxw63b2geztqnjuha2ds===?entryId=ivxhi4tzhizdcnbrgm2tinbs'

CREDENTIAL_VARS = ('PICKEM_EMAIL', 'PICKEM_PASSWORD')


def get_credentials():
    """Return (email, password) from the environment; raise naming every missing or empty variable."""
    values = {name: os.environ.get(name, '').strip() for name in CREDENTIAL_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError('Pickem browser login needs credentials; set the environment variable(s): '
                           + ', '.join(missing))
    return values['PICKEM_EMAIL'], values['PICKEM_PASSWORD']

def build_auth_document(cookies):
    """Reduce browser cookies to the login cookies and wrap them with version and expiry metadata."""
    kept = [{k: c[k] for k in AUTH_COOKIE_FIELDS if k in c} for c in cookies if c.get('name') in AUTH_COOKIE_NAMES]
    expiries = [c['expiry'] for c in kept if c.get('expiry')]
    expires_at = datetime.fromtimestamp(min(expiries), timezone.utc).isoformat() if expiries else None
    return {
        'version': AUTH_VERSION,
        'saved_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': expires_at,
        'cookies': kept,
    }


def save_auth_file(cookies):
    """Save the login cookies as the session. Returns False (leaving any existing session alone) if none qualify
    or the active storage doesn't accept session writes (S3 mode)."""
    document = build_auth_document(cookies)
    if not document['cookies']:
        print('Browser login produced no auth cookies; not updating the saved Pickem session')
        return False
    if not storage.write_session(json.dumps(document, indent=2)):
        print('New Pickem session not saved: the session is read-only in S3 storage mode')
        return False
    print(f'Saved Pickem session (expires {document["expires_at"]})')
    return True


def load_auth_cookies():
    """Return the saved login cookies, or None if the session is missing, unreadable or an unknown version."""
    try:
        text = storage.read_session()
        if text is None:
            print('No saved Pickem session found')
            return None
        document = json.loads(text)
    except (OSError, ValueError):
        print('Saved Pickem session file is unreadable')
        return None
    cookies = document.get('cookies') if isinstance(document, dict) else None
    if not isinstance(document, dict) or document.get('version') != AUTH_VERSION or not isinstance(cookies, list):
        print('Saved Pickem session file has an unrecognized format')
        return None
    cookies = [c for c in cookies if isinstance(c, dict) and c.get('name') and c.get('value')]
    if not cookies:
        print('Saved Pickem session file has no cookies')
        return None
    return cookies


def is_logged_in_pickem_page(response):
    """A 200 login page is the usual failure, so check the final URL and that spreads are actually present."""
    path = urlparse(response.url).path
    return (response.status_code == 200
            and not any(marker in path for marker in LOGGED_OUT_PATHS)
            and 'data-cy="spread"' in response.text)


def fetch_pickem_html_with_session(cookies, url=POOL_URL):
    """Request the pool page with the saved cookies. Returns the page HTML, or None if not logged in or the request failed."""
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'],
                            domain=cookie.get('domain') or '.cbssports.com', path=cookie.get('path') or '/')
    result = apis.call_get_api_with_session(url, session=session, timeout=REQUEST_TIMEOUT_SECONDS)
    if not isinstance(result, tuple):  # the helper returns the exception object on failure
        return None
    response = result[0]
    if not is_logged_in_pickem_page(response):
        print('Saved Pickem session was not accepted')
        return None
    return response.text


def fetch_pickem_html_with_browser():
    """Log in with the browser and refresh the saved session. selenium is imported here so HTTP-only installs don't need it."""
    try:
        import selenium_pa
    except ImportError as err:
        raise RuntimeError('Pickem session is missing or expired and the browser fallback is unavailable '
                           '(selenium is not installed)') from err
    email, password = get_credentials()
    result = selenium_pa.get_pickem_html(email, password)
    if result is None:
        return None
    pickem_html, cookies = result
    save_auth_file(cookies)
    return pickem_html


def get_pickem_html():
    cookies = load_auth_cookies()
    if cookies:
        pickem_html = fetch_pickem_html_with_session(cookies)
        if pickem_html is not None:
            return pickem_html
        print('Falling back to browser login')
    return fetch_pickem_html_with_browser()


# Output format: {'team': 'Dolphins', 'spread': '+12.5'}
def get_pickem_lines(fetch=True):
    if fetch:
        pickem_html = get_pickem_html()
        if pickem_html is None:
            raise RuntimeError('No Pickem page could be obtained: the saved session was not usable and the browser login failed')
        pickem_html = html.fromstring(pickem_html)
        etree.strip_elements(pickem_html, 'script', 'style', with_tail=False)
        print(f'Writing PickEm html to {SAVED_PAGE_KEY} for later use')
        storage.write_text(SAVED_PAGE_KEY, html.tostring(pickem_html, encoding='unicode'))
    else:
        pickem_html = html.fromstring(storage.read_text(SAVED_PAGE_KEY))

    results = []
    for h3 in pickem_html.xpath('//h3'):
        # HTML classes might be mui-style-2wey69 and mui-style-o041sw if you want to use those instead
        fifth_parent = str(html.tostring(h3.xpath('ancestor::*[position()=5]')[0]))
        if 'final' not in fifth_parent and not re.match(r'.*:\d\d<.*', fifth_parent):
            name = h3.text.strip()
            spread = h3.xpath('parent::div/following-sibling::div//div[@data-cy="spread"]/span')[0].text.strip()
            results.append({'team': name, 'spread': spread})

    return results

def has_no_children_with_text(element, text):
    if element is None:
        return True
    if element.text == text:
        return False
    for child in element:
        if has_no_children_with_text(child, text):
            continue
        if child.text == text:
            return False
    return True