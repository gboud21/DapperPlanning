import csv
from datetime import datetime
from typing import List, Optional

def parse_timesheet_csv(filepath: str, engineer_name: str, start_date_str: Optional[str], end_date_str: Optional[str]) -> float:
    """
    Parses a CSV with headers 'Engineer, Date, Hours' and sums hours for a specific engineer
    within the date range [start_date, end_date].
    Dates in CSV are expected to be in MM/DD/YYYY or ISO format.
    """
    total_hours = 0.0
    
    # Try to parse start/end dates
    start_date = None
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        except ValueError:
            pass

    end_date = None
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError:
            pass

    try:
        with open(filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Basic check for headers
                if 'Engineer' not in row or 'Date' not in row or 'Hours' not in row:
                    continue
                
                if row['Engineer'].strip().lower() != engineer_name.strip().lower():
                    continue
                
                # Parse row date
                row_date_str = row['Date'].strip()
                row_date = None
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        row_date = datetime.strptime(row_date_str, fmt)
                        # Make row_date aware if start/end are aware
                        if start_date and start_date.tzinfo:
                            row_date = row_date.replace(tzinfo=start_date.tzinfo)
                        break
                    except ValueError:
                        continue
                
                if not row_date:
                    continue
                
                # Check bounds
                if start_date and row_date < start_date:
                    continue
                if end_date and row_date > end_date:
                    continue
                
                try:
                    total_hours += float(row['Hours'])
                except ValueError:
                    continue
    except (IOError, KeyError):
        pass
        
    return total_hours

def convert_hours_to_fibonacci_weight(hours: float, base_ratio: float = 8.0) -> int:
    """Converts a raw hour estimation into a ceiling-rounded Fibonacci story point weight value."""
    calculated_points = hours / base_ratio
    sequence = [1, 2, 3, 5, 8, 13, 21, 34, 55]
    
    for val in sequence:
        if val >= calculated_points:
            return val
    return sequence[-1]
