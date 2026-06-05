#!/usr/bin/env python3
import sys
from datetime import datetime
from preview import calculate_true_date

def run_edge_cases():
    # Test cases: (Input Business Days, Expected Footprint Description)
    test_cases = [
        ("15", "3 full weeks + skips any intermediate holidays"),
        ("30", "6 full weeks of calendar drift"),
        ("45", "9 full weeks + compounding systemic pauses")
    ]
    
    print("=" * 60)
    print("        TRUDAYZ LOGIC ENGINE: MULTI-WEEK EDGE TEST")
    print("=" * 60)
    
    for days, desc in test_cases:
        true_date = calculate_true_date(days)
        print(f" Quoted Window : [ {days} ] Business Days")
        print(f" Clear Date    : {true_date}")
        print(f" Constraints   : {desc}")
        print("-" * 60)

if __name__ == "__main__":
    run_edge_cases()
