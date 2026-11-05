from lxml import html
# import html as phtml
from datetime import datetime, timedelta
import apis
import util
import statistics
import math
import date_util

OUTPUT_FILE = 'resources/odds_shark.html'

EXCLUDED_BOOKS = [
        # 'BetMGM',
        # 'bet365',
        'DraftKings',
        # 'FanDuel',
        # 'Fanatics Sportsbook',
        # 'BetRivers',
        # 'Caesars',
        'theScore Bet',
        # 'Hard Rock Bet',
    ]

# spread_url = f'https://www.oddsshark.com/api/ticker/nfl?_format=json' (API call that didn't have all the data)
spread_url = 'https://www.covers.com/sport/football/nfl/odds'

def get_spread_html(fetch=True):
    if fetch:
        headers = {
            'Host': 'www.covers.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Pragma': 'no-cache',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',
            'Priority': 'u=0, i',
            'Cache-Control': 'no-cache',
            'TE': 'trailers'
        }

        # params = {
        #     '_format': 'json',
        # }

        body = apis.call_get_api(spread_url, headers)
        if body is not None:
            odds_shark_html = body.text
            print(f'Writing Odds Shark html to {OUTPUT_FILE} for later use')
            util.write_string_to_file(odds_shark_html, OUTPUT_FILE)
            return html.fromstring(odds_shark_html)
        return None
    else:
        with open(OUTPUT_FILE) as file:
            return html.fromstring(file.read())

# Output format: {'team': 'MIA', 'spreads': [{'book': 'Caesars', 'spread': '12.5', 'odds': '-110', 'diff': ''}]}
def get_odds_shark_spreads(fetch=True):
    odds_shark_html = get_spread_html(fetch)
    current_date = datetime.now()
    tuesday = current_date + timedelta(days=(1 - current_date.weekday()) % 7)

    os_spreads_data = []
    # Generates all_events = [{team: '', spreads: [{spread: '', odds: '', book: ''}]}]
    all_events = []
    spreads_table = odds_shark_html.xpath('//table[@id="spread-table"]')[0]
    for event in spreads_table.xpath(".//tr[starts-with(@class, 'oddsGameRow')]"):
        date_cell_result = []
        date_cell_result = event.xpath('.//div[@class="td-cell game-time"]')
        date_cell = date_cell_result[0] if date_cell_result else None
        if date_cell is not None:
            date_spans = []
            date_spans = date_cell.xpath('.//span/text()')
            # format example: <span>Sep 17,&nbsp;</span><span>20:15</span>
            date_string = "{} {}".format(date_spans[0].replace('\xa0', ' ').strip().rstrip(','), date_spans[1].strip())
            if 'Today' in date_string:
                date_string = date_string.replace('Today', current_date.strftime('%b %d'))
            event_date = datetime.strptime(f"{date_string} {current_date.year}", "%b %d %H:%M %Y")
            if current_date.month == 12 and event_date.month == 1 and event_date.day <= 7:
                event_date = event_date.replace(year=event_date.year + 1)
        else:
            event_date = current_date - timedelta(days=1)

        if current_date <= event_date and event_date <= date_util.get_nfl_week_end(date_util.get_nfl_week(current_date)):
            events_row = []
            for participant_name in event.xpath('.//strong/text()'):
                events_row.append({'team': participant_name, 'spreads': [], 'average_spread': None, 'average_mode_odds': None})
            # opening_or_best_or_none_xpath = "boolean(.//div[@class='mobile-only-best-odds' or @class='odds-spread opening' or @class='odds-type-no-odds'])"
            for book_column in event.xpath('.//td[contains(@class, "liveOddsCell")]'):
                spread = get_spreads_from_cell(book_column)
                if not spread is None:
                    if (home := spread.get('home')): events_row[1]['spreads'].append(home)
                    if (away := spread.get('away')): events_row[0]['spreads'].append(away)
            for side in events_row:
                all_events.append(side)

    for event in all_events:
        filtered_spreads = []
        for event_spread in event['spreads']:
            if not event_spread['book'] in EXCLUDED_BOOKS:
                filtered_spreads.append({
                    'book': event_spread['book'],
                    'spread': event_spread['spread'],
                    'odds': event_spread['odds'],
                    'diff': ''
                })
        os_spreads_data.append({'team': event['team'], 'spreads': filtered_spreads})
    
    return os_spreads_data
            
def get_spreads_from_cell(book_column):
    book = book_column.get('data-book')
    home_div_result = book_column.xpath('.//div[contains(@class, "home-cell")]')
    home_div = home_div_result[0] if home_div_result else None
    away_div_result = book_column.xpath('.//div[contains(@class, "away-cell")]')
    away_div = away_div_result[0] if away_div_result else None
    spreads = {}
    for spread_div in [home_div, away_div]:
        if not spread_div is None:
            a = spread_div.xpath('(.//a)[1]')[0]
            spread = spread_div.xpath('.//a[1]/text()[1]')[0].strip()
            odds = a.xpath('.//span[contains(@class, "American")]/text()')[0].strip()
            is_home = 'home' in spread_div.get('class')
            if not spread == 'PK':
                if is_home:
                    spreads['home'] = {'spread': spread, 'odds': odds, 'book': book}
                else:
                    spreads['away'] = {'spread': spread, 'odds': odds, 'book': book}
    return spreads

def get_average_spread(spreads):
    spread_values = [float(item['spread']) for item in spreads if 'spread' in item]
    if spread_values:
        average = sum(spread_values) / len(spread_values)
        return average
    else:
        return None

def get_spread_mode(spreads):
    spread_values = [float(item['spread']) for item in spreads if 'spread' in item]
    if spread_values:
        mode = statistics.mode(spread_values)
        return mode
    else:
        return None

def get_odds_with_spread(spreads, spread_value):
    odds_with_spread = []
    for spread in spreads:
        if math.isclose(float(spread['spread']), float(spread_value), abs_tol=0.01):
            odds_with_spread.append(spread['odds'])
    return odds_with_spread