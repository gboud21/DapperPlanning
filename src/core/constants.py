from enum import Enum

class AgileObjectType(str, Enum):
    PRODUCT = "Product"
    TEAM = "Team"
    MEMBER = "Member"
    EPIC = "Epic"
    FEATURE = "Feature"
    STORY = "Story"

    def __str__(self):
        return self.value

class AgileStatus(str, Enum):
    BACKLOG = "Backlog"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    CLOSED = "Closed"

    def __str__(self):
        return self.value

# Business Logic Defaults & Math Factors
DEFAULT_SPRINT_DAYS = 10
PERCENT_DENOMINATOR = 100.0
DEFAULT_FACTOR_VALUE = 100
