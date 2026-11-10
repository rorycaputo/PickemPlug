"""Local command-line entry point.  Run: python __main__.py [--no-fetch-pickem ...]"""
import argparse

from pickem_plug import FETCH_OPTION_KEYS, RunConfig, run

SOURCE_NAMES = {
    'fetch_pickem': 'Pickem (CBS, via Selenium)',
    'fetch_draftkings': 'Draft Kings',
    'fetch_espnbet': 'ESPN Bet',
    'fetch_oddshark': 'Odds Shark',
}


def build_parser():
    parser = argparse.ArgumentParser(
        description='Compare Pickem spreads against sportsbook lines. '
                    'Every source is fetched live unless switched off; a source switched off '
                    'uses the data saved from its last fetch (in resources/).')
    for key in FETCH_OPTION_KEYS:
        flag = '--' + key.replace('_', '-')
        parser.add_argument(flag, dest=key, action=argparse.BooleanOptionalAction, default=True,
                            help=f'Fetch {SOURCE_NAMES[key]} live; --no-{flag[2:]} uses saved data.')
    parser.add_argument('--override-csv', dest='override_csv_data', metavar='PATH', default=None,
                        help='Skip writing a new CSV and build the HTML from this existing one.')
    return parser


def parse_args(argv=None):
    return RunConfig(**vars(build_parser().parse_args(argv)))


def main(argv=None):
    run(parse_args(argv))


if __name__ == '__main__':
    main()
