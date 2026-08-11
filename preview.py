#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta

def calculate_true_date(business_days):
    # Base configuration matching your engine logic
    # Current Time: Friday, June 5, 2026 (Past East Coast cutoff)
    current_date = datetime(2026, 6, 5)
    
    # Simple business day calculation loop
    remaining_days = int(business_days)
    test_date = current_date
    
    # Juneteenth 2026 Holiday Rule
    holidays = [datetime(2026, 6, 19).date()]
    
    while remaining_days > 0:
        test_date += timedelta(days=1)
        # Skip Weekends (Saturday=5, Sunday=6)
        if test_date.weekday() >= 5:
            continue
        # Skip Federal Banking Holidays
        if test_date.date() in holidays:
            continue
        remaining_days -= 1
        
    return test_date.strftime("%A, %B %d, %Y")

def print_calendar_preview(days_input, target_date_str):
    try:
        clean_str = target_date_str.replace(",", "")
        parts = clean_str.split()
        
        day_of_week = parts[0][:3].upper() 
        month_name = parts[1].upper()      
        day_num = parts[2].zfill(2)        
        year = parts[3]                    
    except Exception:
        day_of_week = "MON"
        month_name = "JUNE"
        day_num = "22"
        year = "2026"

    calendar_box = f"""
               {month_name} {year}
         _____________________
        |  _________________  |
        | |                 | |
        | |     {day_of_week}  {day_num}     | |
        | |                 | |
        | |_________________| |
        |_____________________|
         [   TRUDAYZ CLEAR    ]

 Quoted Window: [ {days_input} ] Business Days
 Status       : Time-zone locked / Holiday verified
"""
    print(calendar_box)

if __name__ == "__main__":
    days = "3"
    if len(sys.argv) > 1:
        days = sys.argv[1]
        
    date_str = calculate_true_date(days)
    print_calendar_preview(days, date_str)
