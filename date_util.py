from datetime import date, datetime, time, timedelta

MNF_KICKOFF = time(20, 30)  # 8:30 PM Eastern


def _day_after_super_bowl(cal_year: int) -> date:
    """Estimated Super Bowl Sunday = 2nd Sunday of Feb; returns the Monday after."""
    feb1 = date(cal_year, 2, 1)
    days_until_sunday = (6 - feb1.weekday()) % 7  # Sunday == 6
    first_sunday = feb1 + timedelta(days=days_until_sunday)
    second_sunday = first_sunday + timedelta(days=7)
    return second_sunday + timedelta(days=1)


def _season_year(dt: datetime) -> int:
    season_year = dt.year - 1 if dt.month <= 2 else dt.year
    if dt.month <= 2:
        cutover = datetime.combine(_day_after_super_bowl(dt.year), time(0, 0))
        if dt >= cutover:
            season_year = dt.year
    return season_year


def _week1_thursday(season_year: int) -> date:
    sept1 = date(season_year, 9, 1)
    days_until_monday = (7 - sept1.weekday()) % 7
    labor_day = sept1 + timedelta(days=days_until_monday)
    return labor_day + timedelta(days=3)


def _boundaries(season_year: int):
    week1_thu = _week1_thursday(season_year)
    boundaries = [datetime.combine(_day_after_super_bowl(season_year), time(0, 0))]
    for n in range(2, 23):
        monday_of_prev_week = week1_thu + timedelta(days=4 + 7 * (n - 2))
        boundaries.append(datetime.combine(monday_of_prev_week, MNF_KICKOFF))
    boundaries.append(
        datetime.combine(_day_after_super_bowl(season_year + 1), time(0, 0))
    )
    return boundaries


def get_nfl_week(dt: datetime) -> int:
    """Estimate the current NFL week number (1-22) from a given datetime."""
    season_year = _season_year(dt)
    boundaries = _boundaries(season_year)

    week_num = 1
    for i, boundary in enumerate(boundaries[:-1], start=1):
        if dt >= boundary:
            week_num = i
        else:
            break
    return week_num


def get_nfl_week_end(week: int, reference_dt: datetime = None) -> datetime:
    """
    Given a week number (1-22), return the datetime marking the END of
    that week - the instant (plus one second) before the next
    week begins. `reference_dt` (defaults to now) disambiguates which
    season's week you mean, since week numbers reset every year.
    """
    if not 1 <= week <= 22:
        raise ValueError("week must be between 1 and 22")

    if reference_dt is None:
        reference_dt = datetime.now()

    season_year = _season_year(reference_dt)
    boundaries = _boundaries(season_year)

    return boundaries[week] + timedelta(seconds=1)