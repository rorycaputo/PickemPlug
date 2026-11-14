import json
import re
import requests
import apis
import date_util
import storage
import time_util

SAVED_DATA_KEY = 'cache/DK_markets_resp.json'

DK_ORIGIN = 'https://sportsbook.draftkings.com'
league_page_url = f'{DK_ORIGIN}/leagues/football/nfl'
lines_url = 'https://sportsbook-nash.draftkings.com/sites/US-IL-SB/api/sportscontent/controldata/league/leagueSubcategory/v1/markets?isBatchable=false&templateVars=88808&eventsQuery=%24filter%3DleagueId%20eq%20%2788808%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%274518%27%29&marketsQuery=%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%274518%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29&include=Events&entity=events'

# Version seen in the 2026-11-14 capture; used when the league page can't supply one.
DK_FALLBACK_CLIENT_VERSION = '2646.5.2'

def get_client_version(session):
    """Read the client version from the league page, falling back to the known value. Never raises.

    Not strictly necessary: the markets API has accepted stale versions for months, and the page is ~2 MB."""
    try:
        page = apis.get(session, league_page_url, headers=apis.NAVIGATION_HEADERS).text
        match = re.search(r'window\.sbwebversion\s*=\s*"(\d+(?:\.\d+)+)"', page)
        if match:
            return match.group(1)
        print('Draft Kings league page has no client version')
    except requests.RequestException as err:
        print(f'Draft Kings league page request failed: {err}')
    print(f'Using fallback Draft Kings client version {DK_FALLBACK_CLIENT_VERSION}')
    return DK_FALLBACK_CLIENT_VERSION

def markets_headers(client_version):
    return {
        'Accept': '*/*',
        'Referer': f'{DK_ORIGIN}/',
        'content-type': 'application/json charset=utf-8',  # malformed, but it's what the site sends
        'x-client-feature': 'leagueSubcategory',
        'x-client-name': 'web',
        'x-client-page': 'league',
        'x-client-version': client_version,
        'x-client-widget-name': 'cms',
        'x-client-widget-version': '3.3.0',
        'x-pe-cn': 'web',
        'x-pe-cv': client_version,
        'x-pe-ep': 'SB',
        'x-pe-loc': 'US-IL',
        'Origin': DK_ORIGIN,
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=4',
    }

def get_lines_json(session, client_version):
    body = apis.get(session, lines_url, headers=markets_headers(client_version))
    print(f'Writing Draft Kings json to {SAVED_DATA_KEY} for later use')
    storage.write_text(SAVED_DATA_KEY, body.text)
    return body.json()

# Output format: {'team': 'MIA Dolphin', 'spread': '12.5', 'odds': '-110', 'diff': ''}
def get_draft_kings_lines(fetch=True, now=None):
    now = now or time_util.now()
    if fetch:
        with apis.new_session() as session:
            client_version = get_client_version(session)
            lines_json = get_lines_json(session, client_version)
    else:
        lines_json = json.loads(storage.read_text(SAVED_DATA_KEY))

    week_marketIds = []
    dk_lines_data = []
    for event in lines_json['events']:
        start_event_date = time_util.parse_utc_iso(event['startEventDate'])
        if date_util.is_in_current_week(start_event_date, now):
            event_id = event['id']
            for market in lines_json['markets']:
                market_id = market['id']
                if market['name'] == 'Spread' and market['eventId'] == event_id:
                    week_marketIds.append(market_id)
    for selection in lines_json['selections']:
        if selection['marketId'] in week_marketIds:
            label = selection['label']
            points = selection.get('points')
            displayOdds_american = selection['displayOdds'].get('american').replace('−', '-')
            # print(f"Label: {label}, Points: {points}, Display Odds (American): {displayOdds_american}")
            dk_lines_data.append({
                'team': label,
                'spread': points,
                'odds': displayOdds_american,
                'diff': ''
            })

    return dk_lines_data