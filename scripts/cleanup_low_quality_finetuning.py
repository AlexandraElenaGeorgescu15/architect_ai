"""
🧹 CLEANUP LOW-QUALITY FINE-TUNING DATA (v3.5.2+)
Removes fine-tuning examples with quality < 80/100.

⚠️ Updated threshold: 90 → 80 (matches generation threshold)
Cloud responses ≥80 are better than local (which failed at <80)

Quality Tiers:
- 90-100: EXCELLENT (priority training)
- 85-89:  GOOD (secondary training)
- 80-84:  ACCEPTABLE (basic training)
- < 80:   Remove (too low quality)

Run this ONCE to clean up old dataset (if any).
"""

import sys
# Enable UTF-8 output on Windows for emoji/Unicode
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

import json
from pathlib import Path
from typing import List, Tuple

QUALITY_THRESHOLD = 80  # Only keep examples with quality >= 80 (matches generation threshold)


def cleanup_finetuning_dataset(dataset_dir: Path = Path("finetune_datasets/cloud_responses")) -> Tuple[int, int, int]:
    """
    Remove low-quality examples from fine-tuning dataset.
    
    Returns:
        (total_files, kept_files, removed_files)
    """
    if not dataset_dir.exists():
        print(f"⚠️ Dataset directory not found: {dataset_dir}")
        return 0, 0, 0
    
    total_files = 0
    kept_files = 0
    removed_files = 0
    removed_list: List[Tuple[str, float]] = []
    
    for json_file in dataset_dir.glob("*.json"):
        total_files += 1
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            quality_score = data.get("quality_score", 0)
            
            if quality_score < QUALITY_THRESHOLD:
                # Remove low-quality example
                json_file.unlink()
                removed_files += 1
                removed_list.append((json_file.name, quality_score))
                print(f"🗑️  Removed: {json_file.name} (quality: {quality_score}/100)")
            else:
                kept_files += 1
                print(f"✅ Kept: {json_file.name} (quality: {quality_score}/100)")
        
        except Exception as e:
            print(f"⚠️ Error processing {json_file.name}: {e}")
    
    return total_files, kept_files, removed_files


def main():
    """Run cleanup on fine-tuning dataset"""
    print("=" * 70)
    print("🧹 FINE-TUNING DATASET CLEANUP")
    print("=" * 70)
    print(f"Quality threshold: {QUALITY_THRESHOLD}/100")
    print(f"Action: Remove examples with quality < {QUALITY_THRESHOLD}")
    print()
    
    dataset_dir = Path("finetune_datasets/cloud_responses")
    
    total, kept, removed = cleanup_finetuning_dataset(dataset_dir)
    
    print()
    print("=" * 70)
    print("📊 CLEANUP SUMMARY")
    print("=" * 70)
    print(f"Total files: {total}")
    print(f"✅ Kept (quality ≥ {QUALITY_THRESHOLD}): {kept}")
    print(f"🗑️  Removed (quality < {QUALITY_THRESHOLD}): {removed}")
    
    if removed > 0:
        print()
        print("✅ CLEANUP COMPLETE!")
        print(f"   Removed {removed} low-quality examples to prevent model degradation.")
        print(f"   {kept} high-quality examples remain for fine-tuning.")
    else:
        print()
        print("✅ ALL EXAMPLES PASSED QUALITY THRESHOLD!")
        print(f"   All {kept} examples are high-quality (≥{QUALITY_THRESHOLD}/100).")
    
    print()
    print("=" * 70)
    print("📝 NEXT STEPS")
    print("=" * 70)
    print("1. ✅ Low-quality examples removed")
    print("2. ⏳ Wait for 50+ examples to accumulate (≥80/100)")
    print("3. 🚀 Fine-tuning will auto-trigger when threshold reached")
    print("4. 📈 Models will improve continuously")
    print()
    print("💡 TIP: System now saves examples with quality ≥ 80/100")
    print("   Quality Tiers:")
    print("   - 90-100: EXCELLENT (priority training)")
    print("   - 85-89:  GOOD (secondary training)")
    print("   - 80-84:  ACCEPTABLE (basic training)")
    print("   Cloud responses are better than local (which failed at <80)!")


if __name__ == "__main__":
    main()

