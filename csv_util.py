import csv
import io
import os
import re
from datetime import datetime, timezone

CSV_STAMP_FORMAT = '%m_%d_%y_%H_%M'
_STAMP_PATTERN = re.compile(r'_(\d{2}_\d{2}_\d{2}_\d{2}_\d{2})_UTC\.csv$')


def stamped_filename(base, instant):
    """`base` plus the instant in UTC, marked `_UTC` so the file's time never depends on the display zone."""
    return f'{base}_{instant.astimezone(timezone.utc).strftime(CSV_STAMP_FORMAT)}_UTC.csv'


def get_generated_at(path):
    """When a CSV was generated, read back from the UTC stamp in its filename as an aware UTC datetime."""
    name = os.path.basename(path)
    match = _STAMP_PATTERN.search(name)
    if not match:
        raise ValueError(f'CSV filename {name!r} has no UTC stamp; expected a name ending in _MM_DD_YY_HH_MM_UTC.csv')
    return datetime.strptime(match.group(1), CSV_STAMP_FORMAT).replace(tzinfo=timezone.utc)


def build_csv(tabulate_dict):
    headers = []
    for event in tabulate_dict:
        for key in event:
            if key not in headers:
                headers.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(tabulate_dict)
    return buffer.getvalue()


def parse_csv(text):
    """CSV text as a list of rows (header row first)."""
    return list(csv.reader(io.StringIO(text, newline='')))