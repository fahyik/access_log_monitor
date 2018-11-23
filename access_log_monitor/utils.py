import datetime
import pytz


def get_utc_now():
    return pytz.UTC.localize(datetime.datetime.utcnow().replace(microsecond=0))
