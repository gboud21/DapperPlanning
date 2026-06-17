import pytest
from src.utils.ai_utils import convert_hours_to_fibonacci_weight, parse_timesheet_csv
import os
import csv

def test_convert_hours_to_fibonacci():
    # 8 hours = 1 point
    assert convert_hours_to_fibonacci_weight(8.0) == 1
    assert convert_hours_to_fibonacci_weight(4.0) == 1
    assert convert_hours_to_fibonacci_weight(9.0) == 2
    assert convert_hours_to_fibonacci_weight(18.5) == 3 # 18.5/8 = 2.31 -> 3
    assert convert_hours_to_fibonacci_weight(40.0) == 5 # 40/8 = 5 -> 5
    assert convert_hours_to_fibonacci_weight(100.0) == 13 # 100/8 = 12.5 -> 13
    assert convert_hours_to_fibonacci_weight(500.0) == 55 # Max in list

def test_parse_timesheet_csv(tmp_path):
    csv_file = tmp_path / "timesheet.csv"
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Engineer', 'Date', 'Hours'])
        writer.writeheader()
        writer.writerow({'Engineer': 'Alice', 'Date': '06/01/2026', 'Hours': '4.0'})
        writer.writerow({'Engineer': 'Alice', 'Date': '06/02/2026', 'Hours': '5.0'})
        writer.writerow({'Engineer': 'Bob', 'Date': '06/01/2026', 'Hours': '8.0'})
        writer.writerow({'Engineer': 'Alice', 'Date': '06/10/2026', 'Hours': '2.0'})
    
    # Alice between 06/01 and 06/05
    hours = parse_timesheet_csv(str(csv_file), 'Alice', '2026-06-01T00:00:00Z', '2026-06-05T23:59:59Z')
    assert hours == 9.0
    
    # Bob
    hours = parse_timesheet_csv(str(csv_file), 'Bob', '2026-06-01T00:00:00Z', '2026-06-05T23:59:59Z')
    assert hours == 8.0
    
    # Alice all time
    hours = parse_timesheet_csv(str(csv_file), 'Alice', None, None)
    assert hours == 11.0
