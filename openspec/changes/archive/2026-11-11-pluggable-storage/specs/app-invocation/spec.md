# Spec Delta

## MODIFIED Requirements

### Requirement: Run result is returned
A run SHALL return a summary containing at least the NFL week number and the storage keys of the CSV and HTML readout it used (for example `out/csv/spreads_output_11_11_26_18_00_UTC.csv` and `out/readout.html`), in the same form in either storage mode. When an override CSV is given, the CSV key SHALL be that override. The Lambda handler SHALL return that summary as a JSON-serializable value.

#### Scenario: Handler return value
- **WHEN** the handler completes a run
- **THEN** it returns a dictionary with the week number, CSV key and HTML key

#### Scenario: Same keys in both modes
- **WHEN** equivalent runs complete in local mode and in S3 mode
- **THEN** both summaries report `out/readout.html` as the HTML key and a CSV key under `out/csv/`
