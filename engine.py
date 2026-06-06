import datetime
from zoneinfo import ZoneInfo

# Official 2026 Federal Reserve Banking Holidays
FED_HOLIDAYS_2026 = {
    datetime.date(2026, 1, 1),   # New Year's Day
    datetime.date(2026, 1, 19),  # MLK Jr. Day
    datetime.date(2026, 2, 16),  # Presidents' Day
    datetime.date(2026, 5, 25),  # Memorial Day
    datetime.date(2026, 6, 19),  # Juneteenth
    datetime.date(2026, 7, 3),   # Independence Day (Observed)
    datetime.date(2026, 9, 7),   # Labor Day
    datetime.date(2026, 10, 12), # Columbus Day
    datetime.date(2026, 11, 11), # Veterans Day
    datetime.date(2026, 11, 26), # Thanksgiving
    datetime.date(2026, 12, 25), # Christmas Day
}

def draw_visual_timeline(days_needed):
    now_pacific = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    now_eastern = now_pacific.astimezone(ZoneInfo("America/New_York"))
    
    print("\n" + "="*45)
    print(f" LOGGED: {now_pacific.strftime('%I:%M %p')} PT  |  BANK CLOCK: {now_eastern.strftime('%I:%M %p')} ET")
    print("="*45)
    
    cutoff_hour_eastern = 14
    current_date = now_pacific
    
    # Check Cut-off
    if now_eastern.hour >= cutoff_hour_eastern:
        print(" STATUS: 🛑 AFTER CUT-OFF (Today is dead space)")
        current_date += datetime.timedelta(days=1)
    else:
        print(" STATUS: 🟢 BEFORE CUT-OFF (Today is operational)")
        
    print("\nPROCESSING TIMELINE CONVEYOR BELT:")
    print("─" * 45)
    
    days_counted = 0
    test_date = current_date.date()
    
    # Map out every calendar day step-by-step
    while days_counted < days_needed:
        test_date += datetime.timedelta(days=1)
        day_str = test_date.strftime('%a, %b %d')
        
        # Scenario 1: Weekend
        if test_date.weekday() >= 5:
            print(f" ⏳ {day_str} -> [ WEEKEND ] ⏩ Skipping...")
            continue
            
        # Scenario 2: Holiday
        if test_date in FED_HOLIDAYS_2026:
            print(f" 🛑 {day_str} -> [ BANK HOLIDAY ] ⏸️ Paused...")
            continue
            
        # Scenario 3: Valid Business Day
        days_counted += 1
        if days_counted == days_needed:
            print(f" 🎉 {day_str} -> [ BUSINESS DAY {days_counted} ] 🏁 TARGET DELIVERY")
        else:
            print(f" ⚡ {day_str} -> [ BUSINESS DAY {days_counted} ] ✅ Moving...")
            
    print("─" * 45)
    print(f" TRUE CLEARING COMPLETION: {test_date.strftime('%A, %B %d, %Y')}")
    print("="*45)

print("=== VISUAL TIMELINE BUILDER ===")
try:
    days_input = int(input("Enter business days to map out (e.g., 10): "))
    draw_visual_timeline(days_input)
except ValueError:
    print("\nPlease enter a simple number.")
