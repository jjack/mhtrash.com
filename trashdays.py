import json
import json
import datetime
import dateutil.relativedelta as rel
from jinja2 import Environment, FileSystemLoader
from dateutil.rrule import rrule, WEEKLY
from pytz import timezone

BASE_DIR_WEB = "/var/www/html/trashdays.com"
BASE_DIR_APP = "/opt/trashdays.com"
TEMPLATE = "trashdays.jinja"

TZ = timezone("US/Central")
RECYCLING_EPOCH = TZ.localize(datetime.datetime(2021, 3, 16))
TODAY = datetime.datetime.now(TZ).replace(hour=0,
                                         minute=0,
                                         second=0,
                                         microsecond=0)

TUESDAY = 1
WEDNESDAY = 2

class TrashDays():
    def _generate_recycling_days(self) -> list:
        """
        Recycling comes every other Tuesday - unless it's a holiday.

        :return: List of all possible recycling days starting from a known date
                 in the past, continuing until two weeks from today
        :rtype: list
        """
        return map(lambda x: self._holiday_adjust(x),
                   rrule(dtstart=RECYCLING_EPOCH,
                         until=TODAY + datetime.timedelta(days=14),
                         freq=WEEKLY,
                         interval=2))

    def _determine_upcoming_trash_day(self) -> datetime:
        """
        Trash comes every Tuesday unless that Tuesday is a holiday, then it
        comes on Wednesday.

        :return: The upcoming trash day
        :rtype: datetime
        """
        if TODAY.weekday() == TUESDAY:
            # today is a trash day - but it might be a holiday
            return self._holiday_adjust(TODAY)
        elif TODAY.weekday() == WEDNESDAY:
            # today is the day after a trash day - it could be a holiday
            # makeup day if yeseterday was an observed holiday
            yesterday = TODAY - rel.relativedelta(days=1)
            if self._is_observed_holiday(yesterday):
                return TODAY

        # otherwise just use next tuesday
        return self._holiday_adjust(
        TODAY + rel.relativedelta(days=1, weekday=rel.TU))

    def _is_observed_holiday(self, dt) -> bool:
        """
        Al Clawson is closed on Thanksgiving, Christmas, and New Year's Day,
        making their trash & recycling pickups on the next day. Since our
        pickup day is Tuesday, we can ignore Thanksgiving, a Thursday-only
        holiday.

        :param dt: The datetime object to compare against
        :type datetime: required
        :return: Whether or not this is an observed holiday
        :rtype: bool
        """
        return (dt.month == 12 and dt.day == 25) or 
               (dt.month == 1 and dt.day == 1)

    def _holiday_adjust(self, dt) -> datetime:
        """
        Take a look at a given datetime object and increment it to the next
        day if it's on one of our observed holidays.

        :param dt: The datetime object to look at
        :type datetime: required
        :return: A (possibly) adjusted datetime object
        :rtype: datetime
        """
        if self._is_observed_holiday(dt):
            return dt + datetime.timedelta(days=1)
        return dt

    def _render_params(self, trash_day) -> dict:
        """
        Render a dictionary of intersting values to be written to disk

        :param trash_day: The datetime object for the next trash day
        :type datetime: required
        :return: A dictionary of info about the next trash day
        :rtype: datetime
        """
        params = {
           "trash_day_readable": trash_day.strftime("%A, %B %d %Y"),
           "trash_day": trash_day.strftime("%s"),
           "countdown": (trash_day - TODAY).days,
           "recycling": trash_day in self._generate_recycling_days(),
        }
        return params

    def _write_html(self, params) -> None:
        """
        Use jinja2 to render the static website.

        :param params: Dictionary containing info abut the next trash day
        :type datetime: required
        """
        env = Environment(loader=FileSystemLoader(BASE_DIR_APP))
        template = env.get_template(TEMPLATE)
        rendered = template.render(params)

        path = "{}/index.html".format(BASE_DIR_WEB)
        with open(path, "w") as fh:
            fh.write(rendered)

    def _write_json(self, params) -> None:
        """
        Write out some .json to be consumed by Home Assistant and the like

        :param params: Dictionary containing info abut the next trash day
        :type datetime: required
        """
        json_path = "{}/index.json".format(BASE_DIR_WEB)
        with open(json_path, "w") as fh:
            fh.write(json.dumps(params))

    def run(self) -> None:
        """
        Figure out the next trash day and write the data out to disk.
        """
        upcoming_trash_day = self._determine_upcoming_trash_day()
        params = self._render_params(upcoming_trash_day)

        self._write_html(params)
        self._write_json(params)


if __name__ == "__main__":
    td = TrashDays()
    td.run()
