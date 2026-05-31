
import json
import os
import glob

base_dir = "/home/gboud21/.gemini/tmp/dapperplanning/chats/"
session_ids = [
    "4b4f6921", "0571d1d3", "c05c8a77", "58015ea6", "1e65d041",
    "03d1e6f4", "91cca67f", "2c68ce86", "63241d3e", "ac50193b", "2ed7f3d0"
]

input_price_per_1m = 0.075
output_price_per_1m = 0.30

total_overall_cost = 0

print(f"{'Session ID':<15} | {'Input Tokens':>12} | {'Output Tokens':>12} | {'Cost ($)':>10}")
print("-" * 65)

for sid in session_ids:
    # Find the file that ends with this ID
    pattern = os.path.join(base_dir, f"session-*{sid}.json")
    files = glob.glob(pattern)
    if not files:
        # Fallback to checking the exact directory listing I saw earlier
        # Some might not have session- prefix if they were differently named
        # but the list_directory showed them all with session- prefix
        print(f"File for session {sid} not found.")
        continue
    
    file_path = files[0]
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        session_input_tokens = 0
        session_output_tokens = 0
        
        for msg in data.get('messages', []):
            if msg.get('type') == 'gemini':
                tokens = msg.get('tokens', {})
                input_t = tokens.get('input', 0)
                # Including thoughts and tool tokens in output as they are generated
                output_t = tokens.get('output', 0) + tokens.get('thoughts', 0) + tokens.get('tool', 0)
                
                session_input_tokens += input_t
                session_output_tokens += output_t
        
        session_cost = (session_input_tokens / 1_000_000) * input_price_per_1m + \
                       (session_output_tokens / 1_000_000) * output_price_per_1m
        
        total_overall_cost += session_cost
        print(f"{sid:<15} | {session_input_tokens:>12,d} | {session_output_tokens:>12,d} | {session_cost:>10.6f}")
        
    except Exception as e:
        print(f"Error processing session {sid}: {e}")

print("-" * 65)
print(f"{'TOTAL':<15} | {'':>12} | {'':>12} | {total_overall_cost:>10.6f}")
