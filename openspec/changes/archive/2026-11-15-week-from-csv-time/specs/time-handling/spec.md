## ADDED Requirements

### Requirement: Readout week is the week of the CSV's generated time
The NFL week shown in the HTML readout's title and header, and the week returned in the run result, SHALL be the NFL week of the CSV's generated time (the UTC stamp in its filename), never of the time the run happens to be executing. For a run that writes its own CSV the two are the same instant.

#### Scenario: Fresh run
- **WHEN** a run writes a CSV and then the HTML
- **THEN** the week in the HTML title and header, and in the run result, is the NFL week of the instant stamped in that CSV's filename

#### Scenario: Override CSV from an earlier week
- **WHEN** a run is given an override CSV whose UTC stamp falls in an earlier NFL week than the current time
- **THEN** the HTML title and header and the run result show the earlier week, matching the generated time shown on the page

#### Scenario: Run result matches the page
- **WHEN** any run completes
- **THEN** the week in the run result (and so in the Lambda handler's return value) equals the week shown in the HTML
