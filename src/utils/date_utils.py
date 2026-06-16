from datetime import datetime, timedelta

def calculate_sprint_business_days(start_str: str, end_str: str) -> int:
    """Calculates inclusive business days (Mon-Fri) between two date strings."""
    if not start_str or not end_str:
        return 10
    try:
        # GitLab ISO dates might contain 'T' or just be 'YYYY-MM-DD'
        start_date = datetime.strptime(start_str.split('T')[0], "%Y-%m-%d")
        end_date = datetime.strptime(end_str.split('T')[0], "%Y-%m-%d")
        
        if start_date > end_date:
            return 10
            
        business_days = 0
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # 0-4 represents Monday through Friday
                business_days += 1
            current += timedelta(days=1)
        return business_days
    except Exception:
        return 10
