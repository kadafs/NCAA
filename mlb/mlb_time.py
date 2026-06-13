import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    import pytz as tz
    def get_mlb_now(): return datetime.datetime.now(tz.timezone('America/New_York'))
else:
    def get_mlb_now(): return datetime.datetime.now(ZoneInfo('America/New_York'))
