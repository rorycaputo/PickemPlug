"""AWS Lambda entry point.  Handler: lambda_function.lambda_handler

Optional event keys (booleans, all default to true): fetch_pickem, fetch_draftkings,
fetch_espnbet, fetch_oddshark. Any other keys in the event are ignored.
"""
from dataclasses import asdict

from pickem_plug import RunConfig, run


def lambda_handler(event, context):
    config = RunConfig.from_event(event)  # raises before any fetching if an option is invalid
    return asdict(run(config))
