import re

def get_odds_float(odds):
    odds_float = float(re.sub(r'[^\d.-]', '', re.sub(r'Even', '100', odds, flags=re.IGNORECASE)))
    if odds_float == -100:
        return 100
    return odds_float

def american_to_decimal(american_odds):
    if american_odds >= 0:
        return 1 + (american_odds / 100)
    else:
        return 1 - (100 / american_odds)
    
def decimal_to_american(decimal_odds):
    if decimal_odds < 2:
        american_odds = round(-100 / (decimal_odds - 1))
    else:
        american_odds = round((decimal_odds -1) * 100)
    return american_odds

def determine_odds_average(odds):
    decimal_odds_values = [american_to_decimal(get_odds_float(odds_value)) for odds_value in odds]
    if decimal_odds_values:
        average = sum(decimal_odds_values) / len(decimal_odds_values)
        return decimal_to_american(average)
    else:
        return None