# Tasks

## 1. Week from the CSV's generated time

- [x] 1.1 In `run()` (`src/pickem_plug.py`), compute `nfl_week` from `csv_util.get_generated_at(output_csv)` after `output_csv` is chosen, instead of from `now`, and use it for the HTML title, header and `RunResult.week`. The live-source calls keep using `now`. Verify by running with `--override-csv` on a CSV from an earlier week and checking the page title, header, generated time and printed/returned week all agree.
- [x] 1.2 Remove the stale `# todo Make it so the week number output is accurate` comment above `override_csv_data` in `RunConfig`. Verify with a grep that it is gone.
- [x] 1.3 Add a `# todo` in `run()` near the override handling noting that an override run still fetches live lines and prints the console table using the current time, and should become a pure re-render of the CSV. Verify the comment is present and describes that limitation.
- [x] 1.4 Verify a normal (non-override) run still produces the same week as before and the existing test suite passes (`python -m unittest discover` from `src`, or the project's usual command). README.md only mentions the return shape, which is unchanged, so no README edit is needed.
