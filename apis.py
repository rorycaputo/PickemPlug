import requests
import json
import base64

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'utf-8',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i'
        # 'Cookie': 'ra_device_id=a16fa42edc5e4a8d95b57dc9d362c44c; ra_entity_id=8907bfaa0d8745e5b7ba97ca916a910e; ra_entity_type=EXTERNAL_USER; ra_session_id=cd7c37b7115c4da28024972f0c2c43a3; ritual_analyticssessionid=ece6f9d37d6d491384744abbe25cde2b; ritual_externalanalyticssessionid=da1d31d0eb1a477fa1a85fa69db0d4cd; ritual_externaluserid=da1d31d0eb1a477fa1a85fa69db0d4cd; rt-lang=en-US'
    }

def call_get_api(url, headers=headers, params=None):
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        return http_err
    except requests.exceptions.ConnectionError as conn_err:
        print(f'Error connecting to the API: {conn_err}')
        return conn_err
    except requests.exceptions.Timeout as timeout_err:
        print(f'Timeout error occurred: {timeout_err}')
        return timeout_err
    except requests.exceptions.RequestException as err:
        print(f'Something went wrong: {err}')
        return err
    
def call_post_api(url, session=requests.Session(), headers=headers, params=None,data=None):
    try:
        response = session.post(url, params, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        print(response)
        return response, session
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        return http_err
    except requests.exceptions.ConnectionError as conn_err:
        print(f'Error connecting to the API: {conn_err}')
        return conn_err
    except requests.exceptions.Timeout as timeout_err:
        print(f'Timeout error occurred: {timeout_err}')
        return timeout_err
    except requests.exceptions.RequestException as err:
        print(f'Something went wrong: {err}')
        return err
    
def call_get_api_with_session(url, headers=headers, params=None, session=requests.Session(), timeout=None):
    try:
        response = session.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response, session
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        return http_err
    except requests.exceptions.ConnectionError as conn_err:
        print(f'Error connecting to the API: {conn_err}')
        return conn_err
    except requests.exceptions.Timeout as timeout_err:
        print(f'Timeout error occurred: {timeout_err}')
        return timeout_err
    except requests.exceptions.RequestException as err:
        print(f'Something went wrong: {err}')
        return err
    
def pickem_login_post(session, u, p):
    url = "https://www.cbssports.com/login?masterProductId=41010&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fkbxw63b2geztqnjuha2ds%3D%3D%3D%3FentryId%3Divxhi4tzhizdcnbrgm2tinbs%26device%3Ddesktop%26device%3Ddesktop"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
        'Accept': 'text/x-component',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://www.cbssports.com/login?masterProductId=41010&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fkbxw63b2geztqnjuha2ds%3D%3D%3D%3FentryId%3Divxhi4tzhizdcnbrgm2tinbs%26device%3Ddesktop%26device%3Ddesktop',
        'Next-Action': '601c2c8161dd24e91b012db39031dadda1b93c878b',
        'Next-Router-State-Tree': '%5B%22%22%2C%7B%22children%22%3A%5B%22login%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D',
        'Origin': 'https://www.cbssports.com',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Cookie': 'cbs_sports_app_webview=false; fly_device=desktop; fly_geo=^{^\^"countryCode^\^":^\^"us^\^",^\^"region^\^":^\^"il^\^",^\^"dma^\^":^\^"602^\^"^}; fly_ab_uid=87bc1f78-bd36-4ce8-8ac0-0191d67553f4; surround=e^%^7C1; XFP_FIRSTPAGE=1; _swb=7b10cf42-cfb5-4956-8113-2c79cfd9cd7d; utag_main=v_id:01995d9040aa003e2c8d4755981805050013a00d00913^$_sn:1^$_se:8^$_ss:0^$_st:1758213195374^$ses_id:1758211358890^%^3Bexp-session^$_pn:3^%^3Bexp-session; randomGroup=90; _swb_consent_=eyJjb2xsZWN0ZWRBdCI6MTc1ODIxMTM1OSwiY29udGV4dCI6eyJjb25maWd1cmF0aW9uSWQiOiJZMkp6WDNOd2IzSjBjeTlqWW5OZmMzQnZjblJ6TDNCeWIyUjFZM1JwYjI0dmRYTmZaMlZ1WlhKaGJDOWxiaTh4TnpVM05qQXpNalUzIiwic291cmNlIjoicGx1Z2lucy5ncGMifSwiZW52aXJvbm1lbnRDb2RlIjoicHJvZHVjdGlvbiIsImlkZW50aXRpZXMiOnsic3diX2Nic19zcG9ydHMiOiI3YjEwY2Y0Mi1jZmI1LTQ5NTYtODExMy0yYzc5Y2ZkOWNkN2QifSwianVyaXNkaWN0aW9uQ29kZSI6InVzX2dlbmVyYWwiLCJwcm9wZXJ0eUNvZGUiOiJjYnNfc3BvcnRzIiwicHVycG9zZXMiOnsiYW5hbHl0aWNzIjp7ImFsbG93ZWQiOiJmYWxzZSIsImxlZ2FsQmFzaXNDb2RlIjoiY29uc2VudF9vcHRvdXQifSwiZXNzZW50aWFsX3NlcnZpY2VzIjp7ImFsbG93ZWQiOiJ0cnVlIiwibGVnYWxCYXNpc0NvZGUiOiJkaXNjbG9zdXJlIn0sImZ1bmN0aW9uYWwiOnsiYWxsb3dlZCI6ImZhbHNlIiwibGVnYWxCYXNpc0NvZGUiOiJjb25zZW50X29wdG91dCJ9LCJzb2NpYWxfbWVkaWEiOnsiYWxsb3dlZCI6ImZhbHNlIiwibGVnYWxCYXNpc0NvZGUiOiJjb25zZW50X29wdG91dCJ9LCJ0YXJnZXRlZF9hZHZlcnRpc2luZyI6eyJhbGxvd2VkIjoiZmFsc2UiLCJsZWdhbEJhc2lzQ29kZSI6ImNvbnNlbnRfb3B0b3V0In19fQ^%^3D^%^3D; gpcsignal=true; usprivacy=1YYN; us_privacy=1YYN; _ketch_consent_v1_=eyJlc3NlbnRpYWxfc2VydmljZXMiOnsic3RhdHVzIjoiZ3JhbnRlZCIsImNhbm9uaWNhbFB1cnBvc2VzIjpbImVzc2VudGlhbF9zZXJ2aWNlcyJdfSwiYW5hbHl0aWNzIjp7InN0YXR1cyI6ImRlbmllZCIsImNhbm9uaWNhbFB1cnBvc2VzIjpbImFuYWx5dGljcyJdfSwiZnVuY3Rpb25hbCI6eyJzdGF0dXMiOiJkZW5pZWQiLCJjYW5vbmljYWxQdXJwb3NlcyI6WyJwcm9kX2VuaGFuY2VtZW50IiwicGVyc29uYWxpemF0aW9uIl19LCJ0YXJnZXRlZF9hZHZlcnRpc2luZyI6eyJzdGF0dXMiOiJkZW5pZWQiLCJjYW5vbmljYWxQdXJwb3NlcyI6WyJiZWhhdmlvcmFsX2FkdmVydGlzaW5nIl19LCJzb2NpYWxfbWVkaWEiOnsic3RhdHVzIjoiZGVuaWVkIiwiY2Fub25pY2FsUHVycG9zZXMiOlsiYmVoYXZpb3JhbF9hZHZlcnRpc2luZyJdfX0^%^3D^',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Priority': 'u=4',
    }
    data = {
        '1_$ACTION_REF_3': '',
        '1_$ACTION_3:0': '{"id":"601c2c8161dd24e91b012db39031dadda1b93c878b","bound":"\$@"}',
        '1_$ACTION_3:1': '[{"isAuth":false,"error":null,"hasMissingFields":false,"missingFields":[],"custId":null,"masterProductId":null,"incorrectCredentials":false,"user":null,"appId":"cbssports","refCode":null}]',
        '1_ACTION_KEY': 'k5351b50c4e8ed7c6110393fe2f7e724c',
        '1_email': u,
        '1_password': base64.b64decode(p).decode('utf-8'),
        '1_g-recaptcha-response': '',
        '1_occupation': '',
        '1_refPage': 'https://picks.cbssports.com/',
        '0': '[{"isAuth":false,"error":null,"hasMissingFields":false,"missingFields":[],"custId":null,"masterProductId":"41010","incorrectCredentials":false,"user":null,"appId":"authex","refCode":""},"\$K1"]'
    }
    
    return call_post_api(url, headers, data).json(), session

def espn_chunk_get(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://sportsbook.thescore.bet/sport/football/organization/united-states/competition/nfl/section/lines',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-origin',
        'TE': 'trailers'
    }

    response, session = call_get_api_with_session(url, headers=headers)
    return response.content.decode('utf-8'), session

def espn_startup_get(startup_sha, session):
    espn_startup_url = f'https://sportsbook.us-il.thescore.bet/graphql/persisted_queries/{startup_sha}?operationName=Startup&variables=%7B%22connectToken%22%3A%221c5d8xeornbn3t5nr57bv5ns141gky%22%2C%22latLongParams%22%3A%7B%22accuracy%22%3A20%2C%22latitude%22%3A39.7638164%2C%22longitude%22%3A-89.7408708%7D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{startup_sha}%22%7D%7D'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://sportsbook.thescore.bet/',
        'content-type': 'application/json',
        'apollographql-client-name': 'espnbet-espnbet-web',
        'apollographql-client-version': '26.21.0', # todo get some of these from previous API calls
        'x-install-id': '2jo2djanm6c11cybd79sjbz1pqup21',
        'x-platform': 'web',
        'x-app-version': '26.21.0',
        'x-app': 'espnbet',
        'x-client': 'espnbet',
        'x-dma': '602',
        'x-device': 'DESKTOP',
        'Origin': 'https://sportsbook.thescore.bet',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'Priority': 'u=4',
        'TE': 'trailers'
    }

    response, session = call_get_api_with_session(espn_startup_url, headers=headers, session=session)
    return response.json(), session

def espn_marketplace_get(marketplace_sha, bearer_token, session):
    espn_marketplace_url = f'https://sportsbook.us-il.thescore.bet/graphql/persisted_queries/{marketplace_sha}?operationName=CompetitionPageSectionLinesTabNode&variables=%7B%22isSubscription%22%3Afalse%2C%22pageType%22%3A%22PAGE%22%2C%22includeRecommendedProps%22%3Atrue%2C%22isBrandingImageEnabled%22%3Atrue%2C%22isNewFeaturedBetParticipantLogoEnabled%22%3Atrue%2C%22isFeaturedBetCarouselHeaderRedesignEnabled%22%3Atrue%2C%22includeStandardizedBoxscore%22%3Atrue%2C%22isCfpRankingEnabled%22%3Atrue%2C%22isCombatSportsRedesignEnabled%22%3Atrue%2C%22isFeaturedMarketCardRedesignEnabled%22%3Atrue%2C%22isDsModelRecommendedPropsEnabled%22%3Afalse%2C%22isBlueprintUiFieldEnabled%22%3Afalse%2C%22includeRichEvent%22%3Atrue%2C%22oddsFormat%22%3A%22AMERICAN%22%2C%22sectionId%22%3A%22Section%3A647c3091-b79f-47bc-a96c-b053cc3a4a6a%22%2C%22selectedFilterId%22%3A%22%22%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{marketplace_sha}%22%7D%7D'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://sportsbook.thescore.bet/',
        'content-type': 'application/json',
        'apollographql-client-name': 'espnbet-espnbet-web',
        'apollographql-client-version': '26.21.0',
        'x-install-id': '2jo2djanm6c11cybd79sjbz1pqup21',
        'x-platform': 'web',
        'x-app-version': '26.21.0',
        'x-app': 'espnbet',
        'x-client': 'espnbet',
        'x-anonymous-authorization': f'Bearer {bearer_token}', 
        'x-dma': '602',
        'x-device': 'DESKTOP',
        'traceparent': '00-000000000000000099a45539b68f223b-07f195826b19197c-01',
        'tracestate': 'dd=s:1;o:rum',
        'x-datadog-origin': 'rum',
        'x-datadog-parent-id': '572403015027857788',
        'x-datadog-sampling-priority': '1',
        'x-datadog-trace-id': '11071067490347852347',
        'Origin': 'https://sportsbook.thescore.bet',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }

    return call_get_api_with_session(espn_marketplace_url, headers=headers, session=session)
