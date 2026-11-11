# Spec Delta

## Purpose

Defines where a run keeps its saved source data, CSV and HTML readout, local files or an S3 bucket, and how that choice is configured, so the same run works on a developer machine and in AWS.

## ADDED Requirements

### Requirement: Storage mode comes from the environment
The system SHALL pick its storage mode from the `PICKEM_STORAGE` environment variable: `local` or `s3`. When the variable is unset or empty, the mode SHALL be `local`. The mode SHALL NOT be a per-run option on the command line or in the Lambda event.

#### Scenario: Unset defaults to local
- **WHEN** a run starts and `PICKEM_STORAGE` is not set
- **THEN** all reads and writes use local files

#### Scenario: S3 mode selected
- **WHEN** a run starts with `PICKEM_STORAGE=s3` and `PICKEM_BUCKET` set
- **THEN** saved source data, the CSV and the HTML readout are read from and written to that bucket

### Requirement: Invalid storage configuration fails before fetching
The system SHALL check the storage configuration at the start of a run and stop with an error, before fetching any source, when `PICKEM_STORAGE` has a value other than `local` or `s3`, or when it is `s3` and `PICKEM_BUCKET` is unset or empty. The error SHALL name the offending variable.

#### Scenario: Unknown mode
- **WHEN** a run starts with `PICKEM_STORAGE=aws`
- **THEN** the run stops with an error naming `PICKEM_STORAGE` and its allowed values, and no source is fetched

#### Scenario: S3 mode without a bucket
- **WHEN** a run starts with `PICKEM_STORAGE=s3` and no `PICKEM_BUCKET`
- **THEN** the run stops with an error naming `PICKEM_BUCKET`, and no source is fetched

### Requirement: Storage key layout
The system SHALL address stored files by key. The saved responses are `cache/pickem.html`, `cache/DK_markets_resp.json`, `cache/espn_markets_resp.json` and `cache/odds_shark.html`. The readout is `out/readout.html`. Each CSV is `out/csv/spreads_output_<MM_DD_YY_HH_MM>_UTC.csv`. In S3 mode the key is the object key in the bucket.

#### Scenario: S3 objects after a full live run
- **WHEN** a live run with all sources completes in S3 mode
- **THEN** the bucket holds the four `cache/` objects, `out/readout.html`, and a new stamped CSV under `out/csv/`

#### Scenario: Readout overwritten, CSVs accumulate
- **WHEN** two runs complete at different minutes
- **THEN** `out/readout.html` holds the second run's readout and both CSVs exist under `out/csv/`

### Requirement: Local mode maps keys to project files
In local mode, a key under `cache/` SHALL map to the same file name under `resources/`, and any other key SHALL map to the same relative path in the project directory. Missing parent directories SHALL be created on write.

#### Scenario: Saved page location unchanged
- **WHEN** a live Pickem fetch completes in local mode
- **THEN** the saved page is written to `resources/pickem.html`

#### Scenario: New CSV location
- **WHEN** a run writes its CSV in local mode
- **THEN** the CSV is written under `out/csv/` and the readout to `out/readout.html`

### Requirement: Saved data is read from the active storage
When a source's fetch option is false, the system SHALL read that source's saved data from the active storage mode. If the saved data does not exist, the run SHALL stop with an error naming the missing key.

#### Scenario: Offline run in S3 mode
- **WHEN** a run in S3 mode sets the DraftKings fetch option to false and `cache/DK_markets_resp.json` exists in the bucket
- **THEN** DraftKings lines are read from that object

#### Scenario: Saved data missing
- **WHEN** a run sets a source's fetch option to false and that source's key does not exist
- **THEN** the run stops with an error naming the key

### Requirement: Stored text is UTF-8
The system SHALL write and read all stored text (saved responses, CSV, HTML) as UTF-8, in both modes.

#### Scenario: Non-ASCII content round trip
- **WHEN** a saved page containing non-ASCII characters is written and later read with the fetch option false
- **THEN** the characters are read back unchanged

### Requirement: S3 objects carry browser-ready metadata
In S3 mode, each written object SHALL have a Content-Type that matches its extension (`.html` as `text/html; charset=utf-8`, `.csv` as `text/csv; charset=utf-8`, `.json` as `application/json`) and `Cache-Control: no-cache`.

#### Scenario: Readout renders in a browser
- **WHEN** `out/readout.html` is written in S3 mode
- **THEN** the object's Content-Type is `text/html; charset=utf-8` and its Cache-Control is `no-cache`

#### Scenario: CSV metadata
- **WHEN** a CSV is written in S3 mode
- **THEN** the object's Content-Type is `text/csv; charset=utf-8`

### Requirement: Readout is built from the run's own rows
The system SHALL build the HTML readout from the table rows the run produced, without reading back the CSV it just wrote. When an override CSV is given, the readout SHALL be built from that CSV, read through the active storage mode, and no new CSV SHALL be written.

#### Scenario: Normal run
- **WHEN** a run writes a new CSV
- **THEN** the readout contains the same rows as that CSV

#### Scenario: Override CSV
- **WHEN** a run is given an override CSV key that exists in the active storage
- **THEN** the readout is built from it, its generated time comes from the key's UTC stamp, and no CSV is written

### Requirement: Local mode needs no AWS library
The system SHALL NOT require the AWS SDK to be installed to import any module or to run in local mode.

#### Scenario: Local run without the SDK
- **WHEN** the AWS SDK is not installed and a run starts in local mode
- **THEN** the run completes normally
