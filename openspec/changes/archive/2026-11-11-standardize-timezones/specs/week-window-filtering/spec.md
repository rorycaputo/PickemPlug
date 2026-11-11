# Spec Delta

## Purpose

Defines how each sportsbook source limits its lines to games in the current NFL week using each event's own start time, so all books are compared over the same set of games.

## ADDED Requirements

### Requirement: Shared current-week window
Draft Kings, ESPN Bet and Odds Shark SHALL each keep an event only when its start instant is at or after the current instant and at or before the end of the current NFL week.

#### Scenario: Event inside the window
- **WHEN** an event starts Sunday 12:00 PM Eastern and the current instant is Thursday of the same week
- **THEN** its lines are included for every source that lists it

#### Scenario: Event in the next week
- **WHEN** an event starts after the end of the current NFL week
- **THEN** its lines are excluded

#### Scenario: Event already started
- **WHEN** an event's start instant is before the current instant
- **THEN** its lines are excluded

### Requirement: ESPN Bet filters by event start time
ESPN Bet SHALL determine each event's start time from the start time ESPN reports for that event (reported in UTC) and apply the shared window. An ESPN event that reports no start time SHALL be excluded. The existing exclusion of closed spread markets SHALL continue to apply.

#### Scenario: ESPN event outside the week
- **WHEN** the ESPN response contains a game that starts after the end of the current NFL week
- **THEN** that game's spreads are not included in the ESPN Bet lines

#### Scenario: ESPN event with no start time
- **WHEN** an ESPN event has no start time
- **THEN** its spreads are excluded

#### Scenario: Closed market still excluded
- **WHEN** an in-window ESPN event has a closed spread market
- **THEN** that market is excluded

### Requirement: Odds Shark relative dates resolve in Eastern
Odds Shark event dates that show only a month, day and time, or the word "Today", SHALL be resolved against the current date in Eastern time, including the year rollover from December to January.

#### Scenario: Today near UTC midnight
- **WHEN** the current instant is 8:00 PM Eastern on November 12 (01:00 UTC on November 13) and Odds Shark lists a game as "Today"
- **THEN** the game's date is November 12

#### Scenario: Year rollover
- **WHEN** the current date in Eastern is December 30 and Odds Shark lists a game on Jan 3
- **THEN** the game's date is January 3 of the following year
