import json

# Check the actual date range in collected data
with open('data/worker_0_singularity_partial.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    posts = data['posts']
    
    if posts:
        print(f"Total posts in worker 0: {len(posts)}")
        print(f"First post date: {posts[0]['created_utc']}")
        print(f"Last post date: {posts[-1]['created_utc']}")
        
        # Convert to readable format
        from datetime import datetime
        first = datetime.fromisoformat(posts[0]['created_utc'].replace('Z', '+00:00'))
        last = datetime.fromisoformat(posts[-1]['created_utc'].replace('Z', '+00:00'))
        
        print(f"\nFirst post: {first}")
        print(f"Last post: {last}")
        print(f"Date range: {(first - last).days} days")
