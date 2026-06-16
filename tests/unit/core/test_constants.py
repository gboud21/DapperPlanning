import pytest
from src.core.constants import AgileObjectType, AgileStatus, PERCENT_DENOMINATOR, DEFAULT_FACTOR_VALUE

def test_agile_object_type_values():
    assert AgileObjectType.PRODUCT == "Product"
    assert AgileObjectType.TEAM == "Team"
    assert AgileObjectType.MEMBER == "Member"
    assert AgileObjectType.EPIC == "Epic"
    assert AgileObjectType.FEATURE == "Feature"
    assert AgileObjectType.STORY == "Story"

def test_agile_status_values():
    assert AgileStatus.BACKLOG == "Backlog"
    assert AgileStatus.IN_PROGRESS == "In Progress"
    assert AgileStatus.IN_REVIEW == "In Review"
    assert AgileStatus.DONE == "Done"
    assert AgileStatus.CLOSED == "Closed"

def test_math_constants():
    assert PERCENT_DENOMINATOR == 100.0
    assert DEFAULT_FACTOR_VALUE == 100

if __name__ == "__main__":
    pytest.main([__file__])
