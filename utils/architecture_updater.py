"""
Auto-update ARCHITECTURE_VISUAL.html with latest system changes
"""
from pathlib import Path
from datetime import datetime
import re


def update_architecture_doc():
    """Update the architecture visual documentation with latest enhancements"""
    arch_file = Path("architect_ai_cursor_poc/ARCHITECTURE_VISUAL.html")
    
    if not arch_file.exists():
        return
    
    html = arch_file.read_text(encoding='utf-8')
    
    # Get current enhancements from the system
    enhancements = get_current_enhancements()
    
    # Find the Latest Enhancements section
    pattern = r'(<div class="banner latest-banner">.*?<ul>)(.*?)(</ul>.*?</div>)'
    
    # Build new enhancements list
    new_items = '\n'.join([f'                    <li>{enh}</li>' for enh in enhancements])
    
    # Replace the enhancements section
    def replacer(match):
        return match.group(1) + '\n' + new_items + '\n                ' + match.group(3)
    
    updated_html = re.sub(pattern, replacer, html, flags=re.DOTALL)
    
    # Update timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_html = re.sub(
        r'Last Updated: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        f'Last Updated: {timestamp}',
        updated_html
    )
    
    # Write back
    arch_file.write_text(updated_html, encoding='utf-8')
    print(f"[INFO] Updated ARCHITECTURE_VISUAL.html at {timestamp}")


def get_current_enhancements():
    """Get list of current system enhancements"""
    return [
        "<strong>Smart Tech Stack Detection:</strong> Automatically detects Angular, React, Vue, .NET, Java, Python projects anywhere in repository",
        "<strong>Generic Root Finding:</strong> Works in any repository structure - detects project root intelligently",
        "<strong>Surgical AI Modifications:</strong> AI makes minimal, targeted code changes without rewriting entire prototypes",
        "<strong>Ultra-Aggressive Cache Busting:</strong> Uses 5-factor cache invalidation (file mtime, size, session timestamp, content hash, dynamic height)",
        "<strong>RAG Index Filtering:</strong> Excludes tool code from indexing, focuses only on actual project code (62 files vs 16K+)",
        "<strong>AI Validation Layer:</strong> Detects when AI returns nonsense tech stacks and automatically falls back to deterministic detection",
        "<strong>Hybrid Detection:</strong> Merges AI analysis with deterministic detection to ensure no tech stacks are missed",
        "<strong>Real-time Prototype Editor:</strong> Chat with AI to modify prototypes incrementally with full change tracking",
        "<strong>Change Verification:</strong> Similarity scores, visual diffs, file verification, keyword search to ensure modifications work",
        "<strong>Trimble Brand Styling:</strong> Modern gradient UI with Trimble blue (#0063A3), high contrast, responsive design"
    ]


if __name__ == "__main__":
    update_architecture_doc()

