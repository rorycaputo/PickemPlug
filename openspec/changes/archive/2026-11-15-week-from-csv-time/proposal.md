## Why

The HTML readout's title and header show an NFL week computed from the current clock (`now()`), while its "generated" time comes from the CSV's UTC filename stamp. In a normal run these agree, but when a run is given an override CSV (`--override-csv`) they can disagree: the page can say "Week 12" next to a generated time from week 9. The week shown should describe the data on the page.

## What Changes

- The NFL week used for the HTML title and header is derived from the CSV's generated time (the UTC stamp in its filename), not from the current time.
- The week in the run result (and so the Lambda handler's return value) uses that same week, so the returned week always matches the page.
- A normal run is unchanged, because its CSV is stamped with the run's own start time.
- Out of scope: in override mode the run still fetches live lines and prints the console table using the current time. A `todo` comment will mark this for a later change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `time-handling`: adds a requirement that the NFL week shown on the readout and returned in the run result is the week of the CSV's generated time.

## Impact

- `src/pickem_plug.py`: `run()` computes the week from the CSV's generated time; the stale `# todo Make it so the week number output is accurate` comment is removed and a new todo about override-mode fetching is added.
- Existing `app-invocation` behavior ("Run result is returned") is unchanged in shape; only which instant the week is derived from changes for override runs.
