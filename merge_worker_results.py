"""
Merge results from all workers into a single file
"""
import json
from glob import glob
from datetime import datetime
import sys

def merge_worker_results(subreddit: str):
    """Merge all worker partial files into one complete file"""
    
    pattern = f"data/worker_*_{subreddit}_partial.json"
    worker_files = sorted(glob(pattern))
    
    if not worker_files:
        print(f"No worker files found matching: {pattern}")
        return
    
    print(f"Found {len(worker_files)} worker files")
    
    merged_data = {
        "scraped_at": datetime.now().isoformat(),
        "subreddit": subreddit,
        "total_workers": len(worker_files),
        "posts": []
    }
    
    total_posts = 0
    total_comments = 0
    
    for file in worker_files:
        print(f"Merging: {file}")
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            posts = data.get('posts', [])
            merged_data['posts'].extend(posts)
            
            total_posts += len(posts)
            for post in posts:
                total_comments += post.get('comments_scraped_count', 0)
    
    # Sort posts by date (newest first)
    merged_data['posts'].sort(
        key=lambda x: x['created_utc'], 
        reverse=True
    )
    
    # Save merged file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/{subreddit}_complete_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, indent=2)
    
    print(f"\n✅ Merge complete!")
    print(f"Output: {output_file}")
    print(f"Total posts: {total_posts}")
    print(f"Total comments: {total_comments}")
    print(f"File size: {len(json.dumps(merged_data)) / 1024 / 1024:.2f} MB")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python merge_worker_results.py <subreddit>")
        print("Example: python merge_worker_results.py python")
        sys.exit(1)
    
    subreddit = sys.argv[1]
    merge_worker_results(subreddit)
