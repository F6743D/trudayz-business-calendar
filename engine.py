import datetime
from zoneinfo import ZoneInfo
from typing import Tuple, List, Dict

HOLIDAYS = {
    2025: {datetime.date(2025,1,1),datetime.date(2025,1,20),datetime.date(2025,2,17),datetime.date(2025,5,26),datetime.date(2025,6,19),datetime.date(2025,7,4),datetime.date(2025,9,1),datetime.date(2025,10,13),datetime.date(2025,11,11),datetime.date(2025,11,27),datetime.date(2025,12,25)},
    2026: {datetime.date(2026,1,1),datetime.date(2026,1,19),datetime.date(2026,2,16),datetime.date(2026,5,25),datetime.date(2026,6,19),datetime.date(2026,7,3),datetime.date(2026,9,7),datetime.date(2026,10,12),datetime.date(2026,11,11),datetime.date(2026,11,26),datetime.date(2026,12,25)},
    2027: {datetime.date(2027,1,1),datetime.date(2027,1,18),datetime.date(2027,2,15),datetime.date(2027,5,31),datetime.date(2027,6,18),datetime.date(2027,7,5),datetime.date(2027,9,6),datetime.date(2027,10,11),datetime.date(2027,11,11),datetime.date(2027,11,25),datetime.date(2027,12,24)},
}

def get_holidays(year): return HOLIDAYS.get(year, set())
def is_business_day(d): return d.weekday() < 5 and d not in get_holidays(d.year)
def get_skip_reason(d):
    if d.weekday()==5: return "Saturday"
    if d.weekday()==6: return "Sunday"
    return "Bank Holiday"

def calculate(business_days, start_date=None):
    if start_date is None: start_date = datetime.date.today()
    current = start_date
    while not is_business_day(current): current += datetime.timedelta(days=1)
    days_counted=0; timeline=[]; test_date=current-datetime.timedelta(days=1)
    weekends_skipped=0; holidays_skipped=0
    while days_counted < business_days:
        test_date += datetime.timedelta(days=1)
        if test_date.weekday()>=5:
            weekends_skipped+=1
            timeline.append({"date":test_date.isoformat(),"label":test_date.strftime("%a %b %d"),"type":"weekend","reason":get_skip_reason(test_date),"day_number":None})
            continue
        if test_date in get_holidays(test_date.year):
            holidays_skipped+=1
            timeline.append({"date":test_date.isoformat(),"label":test_date.strftime("%a %b %d"),"type":"holiday","reason":"Bank Holiday","day_number":None})
            continue
        days_counted+=1
        is_target=days_counted==business_days
        timeline.append({"date":test_date.isoformat(),"label":test_date.strftime("%a %b %d"),"type":"target" if is_target else "business","reason":f"Business Day {days_counted}","day_number":days_counted})
    end_date=test_date
    return {"start_date":start_date.isoformat(),"end_date":end_date.isoformat(),"end_date_formatted":end_date.strftime("%A, %B %d, %Y"),"business_days_requested":business_days,"total_calendar_days":(end_date-start_date).days,"weekends_skipped":weekends_skipped,"holidays_skipped":holidays_skipped,"timeline":timeline}

def get_current_context():
    now_et=datetime.datetime.now(ZoneInfo("America/New_York"))
    now_pt=datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    after=now_et.hour>=14
    return {"time_et":now_et.strftime("%I:%M %p ET"),"time_pt":now_pt.strftime("%I:%M %p PT"),"after_cutoff":after,"cutoff_note":"After 2 PM ET — today does not count." if after else "Before 2 PM ET — today counts.","today":datetime.date.today().isoformat()}
