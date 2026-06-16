import pytest
from src.utils.query_parser import parse_query_to_ast
from unittest.mock import MagicMock

class MockItem:
    def __init__(self, type_name, status, assignee_id=None, label_list=None):
        self.__class__.__name__ = type_name
        self.status = status
        self.assignee_id = assignee_id
        self.labels = label_list or []

@pytest.fixture
def workspace_mock():
    ws = MagicMock()
    member1 = MagicMock()
    member1.name = "Alice"
    member2 = MagicMock()
    member2.name = "Bob"
    ws.members = {1: member1, 2: member2}
    return ws

def test_simple_criteria(workspace_mock):
    item = MockItem("Story", "Backlog")
    ast = parse_query_to_ast('type == Story')
    assert ast.evaluate(item, workspace_mock) is True
    
    ast = parse_query_to_ast('status == Done')
    assert ast.evaluate(item, workspace_mock) is False

def test_boolean_logic(workspace_mock):
    item = MockItem("Story", "Done", assignee_id=1)
    
    ast = parse_query_to_ast('type == Story AND status == Done')
    assert ast.evaluate(item, workspace_mock) is True
    
    ast = parse_query_to_ast('type == Story AND status == Backlog')
    assert ast.evaluate(item, workspace_mock) is False
    
    ast = parse_query_to_ast('status == Backlog OR assignee == Alice')
    assert ast.evaluate(item, workspace_mock) is True

def test_not_operator(workspace_mock):
    item = MockItem("Story", "Backlog")
    ast = parse_query_to_ast('NOT status == Done')
    assert ast.evaluate(item, workspace_mock) is True

def test_parentheses_precedence(workspace_mock):
    # type == "Story" AND NOT (status == "Done" OR assignee == "Unassigned")
    item = MockItem("Story", "Backlog", assignee_id=1) # assignee Alice
    query = 'type == "Story" AND NOT (status == "Done" OR assignee == "Unassigned")'
    ast = parse_query_to_ast(query)
    assert ast.evaluate(item, workspace_mock) is True
    
    item2 = MockItem("Story", "Done", assignee_id=1)
    assert ast.evaluate(item2, workspace_mock) is False
    
    item3 = MockItem("Story", "Backlog", assignee_id=None) # Unassigned
    assert ast.evaluate(item3, workspace_mock) is False

def test_contains_operator(workspace_mock):
    item = MockItem("Story", "Backlog")
    item.title = "Implement login feature"
    
    ast = parse_query_to_ast('title contains login')
    assert ast.evaluate(item, workspace_mock) is True
    
    ast = parse_query_to_ast('title contains logout')
    assert ast.evaluate(item, workspace_mock) is False

def test_syntax_errors():
    with pytest.raises(ValueError, match="Unbalanced Parentheses"):
        parse_query_to_ast("(type == Story")
        
    with pytest.raises(ValueError):
        parse_query_to_ast("type == ") # Missing value
