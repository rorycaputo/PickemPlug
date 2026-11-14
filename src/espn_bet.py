#  The SHA value for each REST call you get from the chunk script: https://espnbet.com/_next/static/chunks/pages/index-46ad9c586d0dff59.js
#  No cookie needed
# Which you can get the filename for via the HTML GET: https://espnbet.com/sport/football/organization/united-states/competition/nfl/section/lines

#  To get bearer token:
# Need to call https://sportsbook-espnbet.us-il.thescore.bet since us defualt one returns error.
# Don't need the cookie on this^
#  token is under `anonymousToken`

#  Then call the operationName=Marketplace api with the auth token
from lxml import html
import json
import re
import apis as apis
import date_util as date_util
import storage as storage
import time_util as time_util

SAVED_DATA_KEY = 'cache/espn_markets_resp.json'

espn_base_url = "https://sportsbook.thescore.bet"
espn_lines_url = f'{espn_base_url}/sport/football/organization/united-states/competition/nfl/section/lines'

def get_espn_html(session):
    return html.fromstring(apis.get(session, espn_lines_url, headers=apis.NAVIGATION_HEADERS).text)

def get_chunk_url(html):
    script_tags = html.xpath('//script[@src[contains(.,"/_next/static/chunks/pages/index-")]]')
    chunk_path = script_tags[0].attrib.get('src') if script_tags else None

    return f'{espn_base_url}{chunk_path}'

def get_sha_token(chunk_blob, op_name):
    re_exp = f'"{op_name}":"([^"]+)"'
    return re.search(re_exp, chunk_blob).group(1)

def get_app_version(chunk_blob):
    match = re.search(r'NEXT_PUBLIC_PACKAGE_JSON_VERSION\s*(?::|\|\|)\s*"(\d+(?:\.\d+)+)"', chunk_blob)
    if not match:
        raise ValueError('Could not find the ESPN Bet app version (NEXT_PUBLIC_PACKAGE_JSON_VERSION) in the page script')
    return match.group(1)

def get_bearer_token(startup_resp):
    return startup_resp['data']['startup']['anonymousToken']

def check_graphql(resp_json, operation):
    """GraphQL reports failures with HTTP 200, so stop on an `errors` list or missing `data`."""
    errors = resp_json.get('errors') if isinstance(resp_json, dict) else None
    if errors or not (isinstance(resp_json, dict) and resp_json.get('data')):
        message = errors[0].get('message', errors[0]) if errors else 'no data in response'
        raise ValueError(f'ESPN Bet {operation} failed: {message}')

def make_api_calls():
    with apis.new_session() as session:
        espn_chunk_url = get_chunk_url(get_espn_html(session))
        espn_chunk = apis.espn_chunk_get(session, espn_chunk_url, espn_lines_url)
        startup_sha = get_sha_token(espn_chunk, 'Startup')
        marketplace_sha = get_sha_token(espn_chunk, 'CompetitionPageSectionLinesTabNode')
        app_version = get_app_version(espn_chunk)
        startup_resp = apis.espn_startup_get(session, startup_sha, app_version)
        check_graphql(startup_resp, 'Startup')
        bearer_token = get_bearer_token(startup_resp)
        espn_marketplace_resp = apis.espn_marketplace_get(session, marketplace_sha, bearer_token, app_version)
    espn_marketplace_json = espn_marketplace_resp.json()
    check_graphql(espn_marketplace_json, 'CompetitionPageSectionLinesTabNode')
    print(f'Writing ESPN Bet json to {SAVED_DATA_KEY} for later use')
    storage.write_text(SAVED_DATA_KEY, espn_marketplace_resp.text)
    return espn_marketplace_json

# Output format: {'team': 'MIA Dolphin', 'spread': 12.5, 'odds': '-110', 'diff': ''}
def get_espn_bet_lines(fetch=True, now=None):
    now = now or time_util.now()
    if fetch:
        espn_marketplace_json = make_api_calls()
    else:
        espn_marketplace_json = json.loads(storage.read_text(SAVED_DATA_KEY))
    for sectionChild in espn_marketplace_json['data']['competitionSection']['sectionChildren']:
        if sectionChild['__typename'] == 'MarketplaceShelf':
            marketplaceShelfChildren = sectionChild['marketplaceShelfChildren']
    espn_spread_data = []
    for marketplaceShelfChild in marketplaceShelfChildren:
        # Markets carry no start time; the game's UTC start is on the card's event.
        start_time = (marketplaceShelfChild.get('fallbackEvent') or {}).get('startTime')
        if not start_time or not date_util.is_in_current_week(time_util.parse_utc_iso(start_time), now):
            continue
        for market in marketplaceShelfChild['pagedMarkets']:
            if market['name'] == 'Game Spread' and not market['status'] == 'CLOSED':
                for selection in market['selections']:
                    espn_spread_data.append({
                        'team': selection['participant']['mediumName'],
                        'spread': selection['points']['decimalPoints'],
                        'odds': selection['odds']['formattedOdds'],
                        'diff': ''
                    })

    return espn_spread_data
