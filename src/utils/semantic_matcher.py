import re

def tokenize_text(text: str) -> set:
    """Normalizes string blocks into lowercase unique alphanumeric token word sets."""
    if not text: return set()
    # Using lowercase and finding all word characters
    return set(re.findall(r'\b\w+\b', text.lower()))

def calculate_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Computes the Jaccard Similarity coefficient between two text blocks."""
    tokens_a = tokenize_text(text_a)
    tokens_b = tokenize_text(text_b)
    
    if not tokens_a and not tokens_b:
        return 1.0
    
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    
    return len(intersection) / len(union) if union else 0.0

def get_top_similar_stories(new_story_text: str, historical_stories: list, limit: int = 3) -> list:
    """Scores historical stories against new text parameters and returns the top matching records."""
    new_tokens = tokenize_text(new_story_text)
    if not new_tokens: 
        return historical_stories[:limit]
    
    scored_stories = []
    for story in historical_stories:
        hist_text = f"{story.title} {story.description}"
        hist_tokens = tokenize_text(hist_text)
        
        intersection = len(new_tokens.intersection(hist_tokens))
        union = len(new_tokens.union(hist_tokens))
        
        score = intersection / union if union > 0 else 0.0
        scored_stories.append((score, story))
        
    # Sort by score descending
    scored_stories.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_stories[:limit]]
