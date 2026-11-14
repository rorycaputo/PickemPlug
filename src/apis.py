import json
from urllib.parse import urlencode
import requests

FIREFOX_VERSION = '159.0'
FIREFOX_UA = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{FIREFOX_VERSION}) Gecko/20100101 Firefox/{FIREFOX_VERSION}'

DEFAULT_TIMEOUT = 30

# Sent on every request. Only encodings requests can decode (br needs the brotli package).
BROWSER_HEADERS = {
    'User-Agent': FIREFOX_UA,
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
}

# Added for top-level page loads, as if typed into the address bar.
NAVIGATION_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
}

def new_session():
    """A session for one source for one run, carrying only the shared browser headers."""
    session = requests.Session()
    session.headers.clear()
    session.headers.update(BROWSER_HEADERS)
    return session


def get(session, url, *, headers=None, params=None, timeout=DEFAULT_TIMEOUT):
    """GET through the source's session. Raises requests.RequestException on network errors and error statuses;
    never retries."""
    response = session.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response


# Unused: the Selenium login replaced this. Captured values have been removed.
# def pickem_login_post(session, u, p):
#     url = "https://www.cbssports.com/login?masterProductId=41010&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fkbxw63b2geztqnjuha2ds%3D%3D%3D%3FentryId%3Divxhi4tzhizdcnbrgm2tinbs%26device%3Ddesktop%26device%3Ddesktop"
#     headers = {
#         'Accept': 'text/x-component',
#         'Referer': url,
#         'Next-Action': '<captured value>',
#         'Next-Router-State-Tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22login%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
#         'Origin': 'https://www.cbssports.com',
#         'Cookie': '<captured value>',
#         'Sec-Fetch-Dest': 'empty',
#         'Sec-Fetch-Mode': 'cors',
#         'Sec-Fetch-Site': 'same-origin',
#         'Priority': 'u=4',
#     }
#     data = {
#         '1_$ACTION_REF_3': '',
#         '1_$ACTION_3:0': r'{"id":"<captured value>","bound":"\$@"}',
#         '1_$ACTION_3:1': '[{"isAuth":false,"error":null,"hasMissingFields":false,"missingFields":[],"custId":null,"masterProductId":null,"incorrectCredentials":false,"user":null,"appId":"cbssports","refCode":null}]',
#         '1_ACTION_KEY': '<captured value>',
#         '1_email': u,
#         '1_password': p,
#         '1_g-recaptcha-response': '',
#         '1_occupation': '',
#         '1_refPage': 'https://picks.cbssports.com/',
#         '0': r'[{"isAuth":false,"error":null,"hasMissingFields":false,"missingFields":[],"custId":null,"masterProductId":"41010","incorrectCredentials":false,"user":null,"appId":"authex","refCode":""},"\$K1"]'
#     }
#     return session.post(url, headers=headers, data=json.dumps(data), timeout=DEFAULT_TIMEOUT).json(), session


ESPN_ORIGIN = 'https://sportsbook.thescore.bet'
ESPN_API_BASE = 'https://sportsbook.us-il.thescore.bet/graphql/persisted_queries'
ESPN_INSTALL_ID = '2jo2djanm6c11cybd79sjbz1pqup21'
ESPN_CONNECT_TOKEN = '1c5d8xeornbn3t5nr57bv5ns141gky'
# One Chicago (West Loop) visitor: the DMA and the reported location must change together.
ESPN_GEO = {'dma': '602', 'latitude': 41.8838214, 'longitude': -87.6517493, 'accuracy': 20}
ESPN_MARKETPLACE_VARIABLES = {
    'isSubscription': False,
    'pageType': 'PAGE',
    'includeRecommendedProps': True,
    'isBrandingImageEnabled': True,
    'isNewFeaturedBetParticipantLogoEnabled': True,
    'isFeaturedBetCarouselHeaderRedesignEnabled': True,
    'includeStandardizedBoxscore': True,
    'isCfpRankingEnabled': True,
    'isCombatSportsRedesignEnabled': True,
    'isFeaturedMarketCardRedesignEnabled': True,
    'isDsModelRecommendedPropsEnabled': False,
    'isBlueprintUiFieldEnabled': False,
    'includeRichEvent': True,
    'oddsFormat': 'AMERICAN',
    'sectionId': 'Section:647c3091-b79f-47bc-a96c-b053cc3a4a6a',
    'selectedFilterId': '',
}


def espn_api_headers(app_version):
    return {
        'Accept': 'application/json',
        'Referer': f'{ESPN_ORIGIN}/',
        'content-type': 'application/json',
        'apollographql-client-name': 'espnbet-espnbet-web',
        'apollographql-client-version': app_version,
        'x-install-id': ESPN_INSTALL_ID,
        'x-platform': 'web',
        'x-app-version': app_version,
        'x-app': 'espnbet',
        'x-client': 'espnbet',
        'x-dma': ESPN_GEO['dma'],
        'x-device': 'DESKTOP',
        'Origin': ESPN_ORIGIN,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=4',
    }


def espn_persisted_query_url(sha, operation, variables):
    compact = {'separators': (',', ':')}
    query = urlencode({
        'operationName': operation,
        'variables': json.dumps(variables, **compact),
        'extensions': json.dumps({'persistedQuery': {'version': 1, 'sha256Hash': sha}}, **compact),
    })
    return f'{ESPN_API_BASE}/{sha}?{query}'


def espn_chunk_get(session, url, referer):
    headers = {
        'Accept': '*/*',
        'Referer': referer,
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
    }
    return get(session, url, headers=headers).content.decode('utf-8')


def espn_startup_get(session, startup_sha, app_version):
    variables = {
        'connectToken': ESPN_CONNECT_TOKEN,
        'latLongParams': {k: ESPN_GEO[k] for k in ('accuracy', 'latitude', 'longitude')},
    }
    url = espn_persisted_query_url(startup_sha, 'Startup', variables)
    return get(session, url, headers=espn_api_headers(app_version)).json()


def espn_marketplace_get(session, marketplace_sha, bearer_token, app_version):
    url = espn_persisted_query_url(marketplace_sha, 'CompetitionPageSectionLinesTabNode', ESPN_MARKETPLACE_VARIABLES)
    headers = espn_api_headers(app_version)
    headers['x-anonymous-authorization'] = f'Bearer {bearer_token}'
    return get(session, url, headers=headers)
