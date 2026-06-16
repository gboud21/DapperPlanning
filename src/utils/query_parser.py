import re
from typing import List, Any, Optional

class QueryNode:
    """Base Abstract Syntax Tree node for logical item evaluation passes."""
    def evaluate(self, item: Any, workspace: Any) -> bool:
        raise NotImplementedError

class CriteriaNode(QueryNode):
    def __init__(self, field: str, operator: str, value: str):
        self.field = field.lower()
        self.operator = operator.lower()
        self.value = value.strip('"\'')

    def evaluate(self, item: Any, workspace: Any) -> bool:
        # Extract attribute values dynamically from item types
        attr_val = ""
        if self.field == "type":
            attr_val = item.__class__.__name__
        elif self.field == "assignee":
            assignee_id = getattr(item, 'assignee_id', None)
            member = workspace.members.get(assignee_id) if assignee_id else None
            attr_val = member.name if member else "Unassigned"
        elif self.field == "label":
            labels = getattr(item, 'labels', [])
            if self.operator == "==": return any(self.value.lower() == l.lower() for l in labels)
            if self.operator == "!=": return all(self.value.lower() != l.lower() for l in labels)
            if self.operator == "contains":
                return any(self.value.lower() in l.lower() for l in labels)
            if self.operator == "not contains":
                return not any(self.value.lower() in l.lower() for l in labels)
            return False
        else:
            attr_val = str(getattr(item, self.field, ""))

        attr_val_lower = attr_val.lower()
        value_lower = self.value.lower()

        if self.operator == "==": return attr_val_lower == value_lower
        if self.operator == "!=": return attr_val_lower != value_lower
        if self.operator == "contains": return value_lower in attr_val_lower
        if self.operator == "not contains": return value_lower not in attr_val_lower
        return False

class LogicalNode(QueryNode):
    def __init__(self, left: QueryNode, conjunction: str, right: QueryNode):
        self.left = left
        self.conjunction = conjunction.upper() # "AND" or "OR"
        self.right = right

    def evaluate(self, item: Any, workspace: Any) -> bool:
        if self.conjunction == "AND":
            return self.left.evaluate(item, workspace) and self.right.evaluate(item, workspace)
        return self.left.evaluate(item, workspace) or self.right.evaluate(item, workspace)

class NotNode(QueryNode):
    def __init__(self, node: QueryNode):
        self.node = node

    def evaluate(self, item: Any, workspace: Any) -> bool:
        return not self.node.evaluate(item, workspace)

class EmptyNode(QueryNode):
    def evaluate(self, item: Any, workspace: Any) -> bool:
        return True

def tokenize(query_str: str) -> List[str]:
    """Splits the query string into tokens."""
    # Pattern to match: parentheses, multi-word operators (not contains), 
    # single operators (==, !=, contains), 
    # logical connectives (AND, OR, NOT), and strings (quoted or unquoted words)
    token_pattern = r'\s*(not contains|contains|==|!=|AND|OR|NOT|\(|\)|"[^"]*"|\'[^\']*\'|[a-zA-Z0-9_]+)\s*'
    tokens = re.findall(token_pattern, query_str, re.IGNORECASE)
    return [t.strip() for t in tokens if t.strip()]

class Parser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Optional[str]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected: Optional[str] = None) -> str:
        token = self.current_token()
        if token is None:
             raise ValueError("Unexpected end of input")
        if expected and token.upper() != expected.upper():
             raise ValueError(f"Expected '{expected}' but found '{token}'")
        self.pos += 1
        return token

    def parse_expression(self) -> QueryNode:
        return self.parse_or()

    def parse_or(self) -> QueryNode:
        node = self.parse_and()
        while self.current_token() and self.current_token().upper() == "OR":
            self.consume("OR")
            right = self.parse_and()
            node = LogicalNode(node, "OR", right)
        return node

    def parse_and(self) -> QueryNode:
        node = self.parse_not()
        while self.current_token() and self.current_token().upper() == "AND":
            self.consume("AND")
            right = self.parse_not()
            node = LogicalNode(node, "AND", right)
        return node

    def parse_not(self) -> QueryNode:
        if self.current_token() and self.current_token().upper() == "NOT":
            self.consume("NOT")
            return NotNode(self.parse_not())
        return self.parse_primary()

    def parse_primary(self) -> QueryNode:
        token = self.current_token()
        if token == "(":
            self.consume("(")
            node = self.parse_expression()
            self.consume(")")
            return node
        
        # Criteria: field operator value
        field = self.consume()
        operator = self.consume()
        # 'not contains' is already a single token due to regex
        value = self.consume()
        return CriteriaNode(field, operator, value)

def parse_query_to_ast(query_str: str) -> QueryNode:
    """Parses text strings into evaluation tree structures."""
    if not query_str.strip():
        return EmptyNode()
    
    tokens = tokenize(query_str)
    if not tokens:
        return EmptyNode()
        
    if tokens.count('(') != tokens.count(')'):
        raise ValueError("Unbalanced Parentheses")
        
    parser = Parser(tokens)
    try:
        ast = parser.parse_expression()
        if parser.pos < len(tokens):
            raise ValueError(f"Unexpected token at end: {tokens[parser.pos]}")
        return ast
    except (IndexError, ValueError) as e:
        raise ValueError(f"{str(e)}")
