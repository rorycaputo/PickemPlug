# html-readout Specification

## Purpose

Defines how the generated HTML readout is presented, so it is legible on phones and desktops and its direction indicators render on mobile WebKit.

## Requirements

### Requirement: Readout renders at device width on mobile
The HTML readout SHALL declare a device-width viewport so mobile browsers display it at normal text size rather than zoomed out to a desktop-width layout. On narrow screens the page SHALL use reduced page and table-cell padding, and the table SHALL scroll horizontally within the page rather than shrinking the page.

#### Scenario: Viewed on a phone
- **WHEN** the readout is opened on a phone-width screen
- **THEN** the page is laid out at the device width, text is legible without zooming, and the table is scrolled sideways within its own container

#### Scenario: Viewed on desktop
- **WHEN** the readout is opened on a desktop-width screen
- **THEN** the page keeps its desktop side margins and table styling, and a table that fits the window looks as it did before

### Requirement: Scrollable table extends to the right edge
When the table is wider than the window, it SHALL extend to the right edge of the window instead of being inset by the page margin, so a clipped column signals that the table scrolls. The right-hand margin SHALL appear after the last column only when the table is scrolled fully to the right. This applies at all window widths.

#### Scenario: Table wider than the window
- **WHEN** the table is wider than the window and is scrolled to the left
- **THEN** the table runs to the right edge of the window with no right margin

#### Scenario: Scrolled fully right
- **WHEN** the table is scrolled fully to the right
- **THEN** a page-margin-sized gap appears after the last column

### Requirement: Space after the preface lines
The readout SHALL leave visible vertical space between the preface lines and the table.

#### Scenario: Preface above the table
- **WHEN** the readout has preface lines
- **THEN** there is a gap between the last preface line and the table

### Requirement: Direction indicators render on mobile WebKit
The readout SHALL indicate value-diff direction using characters that render as glyphs on mobile WebKit (iOS Safari), and SHALL NOT use the characters U+2B9D or U+2B9F. Strength tiers (strong colored, plain, slight) SHALL remain distinguishable as before.

#### Scenario: Positive and negative diffs
- **WHEN** a value diff is large enough to display a direction indicator
- **THEN** it is shown as an up or down triangle (`▲` / `▼`), colored green or red for the strong tier
