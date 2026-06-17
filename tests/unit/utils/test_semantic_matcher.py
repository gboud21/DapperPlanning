import pytest
from src.utils.semantic_matcher import tokenize_text, calculate_jaccard_similarity, get_top_similar_stories
from src.domain.entities import Story, Team

def test_tokenize_text():
    text = "Implement login feature for user authentication."
    tokens = tokenize_text(text)
    assert "login" in tokens
    assert "feature" in tokens
    assert "authentication" in tokens
    assert "implement" in tokens
    assert len(tokens) == 6

def test_jaccard_similarity():
    text_a = "Create new user account"
    text_b = "Update user account profile"
    # Tokens A: {create, new, user, account} (4)
    # Tokens B: {update, user, account, profile} (4)
    # Intersection: {user, account} (2)
    # Union: {create, new, user, account, update, profile} (6)
    # Score: 2/6 = 0.333...
    
    score = calculate_jaccard_similarity(text_a, text_b)
    assert score == pytest.approx(0.333, rel=1e-2)
    
    # Identical
    assert calculate_jaccard_similarity("abc", "abc") == 1.0
    # Completely different
    assert calculate_jaccard_similarity("abc", "xyz") == 0.0

def test_get_top_similar_stories():
    team = Team(name="A")
    s1 = Story(id="1", title="User Login", description="Handle user sign in", team=team)
    s2 = Story(id="2", title="Admin Dashboard", description="Stats for admins", team=team)
    s3 = Story(id="3", title="User Signup", description="Register new account", team=team)
    
    historical = [s1, s2, s3]
    top = get_top_similar_stories("How to login users?", historical, limit=2)
    
    assert len(top) == 2
    assert top[0].id == "1" # Login is most similar
