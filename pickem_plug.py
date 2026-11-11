from dataclasses import dataclass
from typing import Optional
from tabulate import tabulate
import re
import draft_kings
import pickem
import espn_bet
import odds_shark
import spread_odds_converter
import util
import date_util
import time_util
import csv_util
import html_util

# todo get CBS odds at time of go-live

#  todo see if we can just exclude if its false and there's no file saved (or add another bypass setting)

# Names of the per-source fetch options (RunConfig fields, CLI flags, and Lambda event keys).
# A False value means "use that source's previously saved data instead of fetching".
FETCH_OPTION_KEYS = ('fetch_pickem', 'fetch_draftkings', 'fetch_espnbet', 'fetch_oddshark')


@dataclass(frozen=True)
class RunConfig:
    """Everything that can change how a run behaves. Pass one to run()."""
    fetch_pickem: bool = True
    fetch_draftkings: bool = True
    fetch_espnbet: bool = True
    fetch_oddshark: bool = True
    # todo Make it so the week number output is accurate
    override_csv_data: Optional[str] = None

    @classmethod
    def from_event(cls, event):
        """Build a config from a Lambda event. Missing keys use defaults; unknown keys are ignored."""
        if not isinstance(event, dict):
            return cls()
        options = {}
        for key in FETCH_OPTION_KEYS:
            if key in event:
                if not isinstance(event[key], bool):
                    raise ValueError(f"Event key '{key}' must be a boolean, got {type(event[key]).__name__}: {event[key]!r}")
                options[key] = event[key]
        return cls(**options)


@dataclass(frozen=True)
class RunResult:
    week: int
    csv_path: str
    html_path: str


SPREAD_HEADER = 'Spread'
ODDS_HEADER = 'Odds'
DIFF_HEADER = 'Value Diff*'

AVG_ALL = f'Average {DIFF_HEADER}'
DRAFTKINGS_SPREAD_HEADER = f'Draft Kings {SPREAD_HEADER}'
DRAFTKINGS_DIFF_HEADER = f'Draft Kings {DIFF_HEADER}'
DRAFTKINGS_ODDS_HEADER = f'Draft Kings {ODDS_HEADER}'
ESPNBET_SPREAD_HEADER = f'ESPN Bet {SPREAD_HEADER}'
ESPNBET_DIFF_HEADER = f'ESPN Bet {DIFF_HEADER}'
ESPNBET_ODDS_HEADER = f'ESPN Bet {ODDS_HEADER}'

SORT_BY_HEADERS = [AVG_ALL] # Spread Diff Header or AVG_ALL

HTML_HEADER_TEXT = 'Week '
VALUE_DIFF_DISCLAIMER = '* Calculated using AI-researched weights for each point change based on modern era games. Displayed in cents.'
COVERS_DISCLAIMER = '\u2020 From Covers.com'

CSV_OUTPUT_FILENAME = './out/spreads_output'
HTML_READOUT_FILENAME = './out/readout.html'

def run(config=None):
    config = config or RunConfig()
    time_util.get_display_tz()
    if config.override_csv_data is not None:
        csv_util.get_generated_at(config.override_csv_data)
    now = time_util.now()
    nfl_week = date_util.get_nfl_week(now)
    pickem_lines = pickem.get_pickem_lines(config.fetch_pickem)
    os_lines = odds_shark.get_odds_shark_spreads(config.fetch_oddshark, now)
    dk_lines = draft_kings.get_draft_kings_lines(config.fetch_draftkings, now)
    espn_lines = espn_bet.get_espn_bet_lines(config.fetch_espnbet, now)
    print(VALUE_DIFF_DISCLAIMER)
    print(COVERS_DISCLAIMER)

    final_tabulate_table, final_tabulate_dict = build_table(pickem_lines, dk_lines, espn_lines, os_lines)
    # todo - Console encoding: in a piped terminal, print(final_tabulate_table) fails on Windows' cp1252 encoding. That line isn't part of this change. Run with PYTHONUTF8=1, or in a UTF-8 terminal, and it works.
    print(final_tabulate_table)
    # todo Average excluding max and min outliers?
    # todo actual timestamps for each book
    # todo format for email
    # todo make only 'spread' and 'odds' neccessary for the sub-headers so CBS is in there (if we can figure out CBS initial odds)
    if config.override_csv_data is not None:
        output_csv = config.override_csv_data
    else:
        output_csv = csv_util.create_csv(final_tabulate_dict, csv_util.stamped_filename(CSV_OUTPUT_FILENAME, now))
    html_util.create_html(
        csv_filename=output_csv,
        generated_at=csv_util.get_generated_at(output_csv),
        output_filename=HTML_READOUT_FILENAME,
        title=f'{HTML_HEADER_TEXT}{nfl_week} - Pickem',
        header_text=f'{HTML_HEADER_TEXT}{nfl_week}',
        sub_headers=[SPREAD_HEADER, ODDS_HEADER, DIFF_HEADER],
        preface_lines=[VALUE_DIFF_DISCLAIMER, COVERS_DISCLAIMER],
    )
    return RunResult(week=nfl_week, csv_path=output_csv, html_path=HTML_READOUT_FILENAME)

def build_table(pickem_lines, dk_lines, espn_lines, os_lines):
    final_table = []
    for line in pickem_lines:
        dk_team = get_team_from_map(line['team'], 'd')

        final_event_output = {
            'Team': dk_team,
            'PickEm': line['spread'],
            AVG_ALL: '',
        }

        dk_record = get_record(dk_team, dk_lines)
        if dk_record is not None:
            dk_spread_diff = get_spread_diff(line['spread'], dk_record['spread'])
            dk_value_diff = get_value_diff(line['spread'], dk_record['spread'], dk_record['odds'])['cents_gap']
            dk_record['diff'] = dk_value_diff
            final_event_output[DRAFTKINGS_SPREAD_HEADER] = f'{dk_record["spread"]}' #{get_spread_display_arrow(dk_spread_diff)}'
            final_event_output[DRAFTKINGS_ODDS_HEADER] = f'{dk_record["odds"]}' #{get_odds_display_arrow(dk_record["odds"])}'
            final_event_output[DRAFTKINGS_DIFF_HEADER] = f'{dk_record["diff"]}{get_cents_display_arrow(dk_record["diff"])}'

        espn_team = get_team_from_map(line['team'], 'e', 'd') # Names are the same as Draft Kings
        espn_record = get_record(espn_team, espn_lines)
        if espn_record is not None:
            espn_spread_diff = get_spread_diff(line['spread'], espn_record['spread'])
            espn_value_diff = get_value_diff(line['spread'], espn_record['spread'], espn_record['odds'])['cents_gap']
            espn_record['diff'] = espn_value_diff
            final_event_output[ESPNBET_SPREAD_HEADER] = f'{espn_record["spread"]}' #{get_spread_display_arrow(espn_spread_diff)}'
            final_event_output[ESPNBET_ODDS_HEADER] = f'{espn_record["odds"]}' #{get_odds_display_arrow(espn_record["odds"])}'
            final_event_output[ESPNBET_DIFF_HEADER] = f'{espn_record["diff"]}{get_cents_display_arrow(espn_record["diff"])}'

        os_team = get_team_from_map(line['team'], 'o')
        os_record = get_record(os_team, os_lines)
        if os_record is not None:
            for os_spread in os_record['spreads']:
                os_spread_diff = get_spread_diff(line['spread'], os_spread['spread'])
                os_value_diff = get_value_diff(line['spread'], os_spread['spread'], os_spread['odds'])['cents_gap']
                os_spread['diff'] = os_value_diff
                final_event_output[f'{os_spread["book"]}\u2020 {SPREAD_HEADER}'] = f'{os_spread["spread"]}' #{get_spread_display_arrow(spread["diff"])}'
                final_event_output[f'{os_spread["book"]}\u2020 {ODDS_HEADER}'] = f'{os_spread["odds"]}' #{get_odds_display_arrow(spread["odds"])}'
                final_event_output[f'{os_spread["book"]}\u2020 {DIFF_HEADER}'] = f'{os_spread["diff"]}{get_cents_display_arrow(os_spread["diff"])}'

        average_diff_lambda = lambda event: (lambda diff_keys: sum(get_diff_from_table(event, k) for k in diff_keys) / len(diff_keys) if diff_keys else 0)(
            [k for k in event.keys() if (k.endswith(DIFF_HEADER) and not k == AVG_ALL)]
        )
        diff_average = round(average_diff_lambda(final_event_output), 2)
        final_event_output[AVG_ALL] = f'{diff_average}{get_cents_display_arrow(diff_average)}'

        final_table.append(final_event_output)

    sort_lambda = lambda x: (-get_diff_from_table(x, SORT_BY_HEADERS[0]))
    sorted_final_table = sorted(final_table, key=sort_lambda)
    table = tabulate(sorted_final_table, headers="keys", tablefmt="fancy_outline")
    return table, sorted_final_table

def get_diff_from_table(table, spread_header):
    return float(re.sub(r'[^\d.-]', '', table[spread_header]))

def get_odds_from_table(table, odds_header):
    return util.get_odds_float(table[odds_header])

def determine_odds_average(x):
    if get_diff_from_table(x, DRAFTKINGS_DIFF_HEADER) == get_diff_from_table(x, ESPNBET_DIFF_HEADER):
        return (util.american_to_decimal(get_odds_from_table(x, DRAFTKINGS_ODDS_HEADER)) + util.american_to_decimal(get_odds_from_table(x, ESPNBET_ODDS_HEADER))) / 2
    elif get_diff_from_table(x, DRAFTKINGS_DIFF_HEADER) > get_diff_from_table(x, ESPNBET_DIFF_HEADER):
        return util.american_to_decimal(get_odds_from_table(x, DRAFTKINGS_ODDS_HEADER))
    else:
        return util.american_to_decimal(get_odds_from_table(x, ESPNBET_ODDS_HEADER))

name_map = [
    {
        'p': 'Dolphins',
        'd': 'MIA Dolphins',
        'o': 'MIA'
    },
    {
        'p': 'Bills',
        'd': 'BUF Bills',
        'o': 'BUF'
    },
    {
        'p': 'Falcons',
        'd': 'ATL Falcons',
        'o': 'ATL'
    },
    {
        'p': 'Panthers',
        'd': 'CAR Panthers',
        'o': 'CAR'
    },
    {
        'p': 'Packers',
        'd': 'GB Packers',
        'o': 'GB'
    },
    {
        'p': 'Browns',
        'd': 'CLE Browns',
        'o': 'CLE'
    },
    {
        'p': 'Texans',
        'd': 'HOU Texans',
        'o': 'HOU'
    },
    {
        'p': 'Jaguars',
        'd': 'JAX Jaguars',
        'o': 'JAC'
    },
    {
        'p': 'Bengals',
        'd': 'CIN Bengals',
        'o': 'CIN'
    },
    {
        'p': 'Vikings',
        'd': 'MIN Vikings',
        'o': 'MIN'
    },
    {
        'p': 'Steelers',
        'd': 'PIT Steelers',
        'o': 'PIT'
    },
    {
        'p': 'Patriots',
        'd': 'NE Patriots',
        'o': 'NE'
    },
    {
        'p': 'Rams',
        'd': 'LA Rams',
        'o': 'LA'
    },
    {
        'p': 'Eagles',
        'd': 'PHI Eagles',
        'o': 'PHI'
    },
    {
        'p': 'Jets',
        'd': 'NY Jets',
        'o': 'NYJ'
    },
    {
        'p': 'Buccaneers',
        'd': 'TB Buccaneers',
        'o': 'TB'
    },
    {
        'p': 'Colts',
        'd': 'IND Colts',
        'o': 'IND'
    },
    {
        'p': 'Titans',
        'd': 'TEN Titans',
        'o': 'TEN'
    },
    {
        'p': 'Raiders',
        'd': 'LV Raiders',
        'o': 'LV'
    },
    {
        'p': 'Commanders',
        'd': 'WAS Commanders',
        'o': 'WAS',
        'e': 'WSH Commanders'
    },
    {
        'p': 'Broncos',
        'd': 'DEN Broncos',
        'o': 'DEN'
    },
    {
        'p': 'Chargers',
        'd': 'LA Chargers',
        'o': 'LAC'
    },
    {
        'p': 'Saints',
        'd': 'NO Saints',
        'o': 'NO'
    },
    {
        'p': 'Seahawks',
        'd': 'SEA Seahawks',
        'o': 'SEA'
    },
    {
        'p': 'Cowboys',
        'd': 'DAL Cowboys',
        'o': 'DAL'
    },
    {
        'p': 'Bears',
        'd': 'CHI Bears',
        'o': 'CHI'
    },
    {
        'p': 'Cardinals',
        'd': 'ARI Cardinals',
        'o': 'ARI'
    },
    {
        'p': '49ers',
        'd': 'SF 49ers',
        'o': 'SF'
    },
    {
        'p': 'Chiefs',
        'd': 'KC Chiefs',
        'o': 'KC'
    },
    {
        'p': 'Giants',
        'd': 'NY Giants',
        'o': 'NYG'
    },
    {
        'p': 'Lions',
        'd': 'DET Lions',
        'o': 'DET'
    },
    {
        'p': 'Ravens',
        'd': 'BAL Ravens',
        'o': 'BAL'
    }
]

def get_team_from_map(pickemTeam, key, backup_key=None):
    for item in name_map:
        if item['p'] == pickemTeam:
            if item.get(key) is not None: return item[key]
            elif (backup_key is not None) and item.get(backup_key) is not None: return item[backup_key]
    return None

def get_record(team, data):
    for item in data:
        if item['team'] == team:
            return item
    return None

def get_spread_diff(pickemSpread, dkSpread):
    #  Edit: there are ties in regular season
    # offset = 0
    # pickemSpread = float(pickemSpread)
    # dkSpread = float(dkSpread)
    # if (pickemSpread < 0 and pickemSpread > -1 and dkSpread > pickemSpread) or (dkSpread > 0 and dkSpread < 1 and pickemSpread < dkSpread):
    #     offset = 1
    # elif (pickemSpread > 0 and pickemSpread < 1 and dkSpread < pickemSpread) or (dkSpread < 0 and dkSpread > -1 and pickemSpread > dkSpread):
    #     offset = -1

    # return str(pickemSpread - dkSpread + offset) + ('*' if offset != 0 else '')
    return float(pickemSpread) - float(dkSpread)

def get_value_diff(pickemSpread, bookSpread, bookOdds):
    if (str(bookOdds).lower() == 'even'):
            bookOdds = 100
    return spread_odds_converter.price_gap(float(pickemSpread), -110, float(bookSpread), float(bookOdds))

def get_spread_display_arrow(spread_diff):
    if isinstance(spread_diff, str):
        spread_diff = float(re.sub(r'[^\d.-]', '',spread_diff))
    display_arrow = ''
    if spread_diff >= 1:
        display_arrow = '\033[92m \u2B9D\033[00m'
    elif spread_diff >=0.5 and spread_diff < 1:
        display_arrow = ' \u2B9D'
    elif spread_diff > 0 and spread_diff < 0.5:
        display_arrow = ' ^'
    if spread_diff <= -1:
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif spread_diff <= -0.5 and spread_diff > -1:
        display_arrow = ' \u2B9f'
    elif spread_diff < 0 and spread_diff > -0.5:
        display_arrow = ' v'

    return display_arrow

def get_odds_display_arrow(odds):
    display_arrow = ''
    if (str(odds).lower() == 'even'):
        odds = 100
    if float(odds) <= -120:
        display_arrow = '\033[92m \u2B9D\033[00m'
    elif float(odds) <= -115:
        display_arrow = ' \u2B9D'
    elif float(odds) < -110: # Book default
        display_arrow = ' ^'
    elif float(odds) >= -100: # Even
        display_arrow = '\033[91m \u2B9F\033[00m'
    elif float(odds) >= -105:
        display_arrow = ' \u2B9f'
    elif float(odds) > -110:
        display_arrow = ' v'

    return display_arrow

def get_cents_display_arrow(cents_diff):
    display_arrow = ''
    if cents_diff is not None:
        if float(cents_diff) >= 30:
            display_arrow = '\033[92m \u2B9D\033[00m'
        elif float(cents_diff) >= 15:
            display_arrow = ' \u2B9D'
        elif float(cents_diff) >= 5:
            display_arrow = ' ^'
        elif float(cents_diff) <= -30:
            display_arrow = '\033[91m \u2B9F\033[00m'
        elif float(cents_diff) <= -15:
            display_arrow = ' \u2B9f'
        elif float(cents_diff) <= -5:
            display_arrow = ' v'

    return display_arrow
