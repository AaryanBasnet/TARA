"""
Boarding Pass OCR Evaluation
============================

Evaluates the boarding pass scanning accuracy against ground truth samples.

Usage:
    python evaluation/evaluate_boarding_pass.py
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from boarding_pass_tools import extract_boarding_pass_fields, get_ocr_reader

# Configuration
SAMPLES_DIR = "evaluation/boarding_pass_samples"
GROUND_TRUTH_FILE = os.path.join(SAMPLES_DIR, "ground_truth.json")
RESULTS_DIR = "evaluation/results"


def normalize_value(value):
    """Normalize a value for comparison (uppercase, strip whitespace, remove punctuation)."""
    if value is None:
        return ""
    return str(value).upper().strip().replace(" ", "").replace(".", "").replace("-", "").replace(":", "")


def field_matches(extracted, expected, partial_match=True):
    """
    Check if extracted field matches expected value.

    Args:
        extracted: The OCR extracted value
        expected: The ground truth value
        partial_match: Allow partial matching (extracted contains expected or vice versa)

    Returns:
        tuple: (is_match: bool, score: float 0-1)
    """
    if extracted is None and expected is None:
        return True, 1.0
    if extracted is None or expected is None:
        return False, 0.0

    ext_norm = normalize_value(extracted)
    exp_norm = normalize_value(expected)

    # Exact match
    if ext_norm == exp_norm:
        return True, 1.0

    # Partial match
    if partial_match:
        if exp_norm in ext_norm or ext_norm in exp_norm:
            # Calculate similarity based on overlap
            shorter = min(len(ext_norm), len(exp_norm))
            longer = max(len(ext_norm), len(exp_norm))
            if longer > 0:
                return True, shorter / longer

    return False, 0.0


def evaluate_single_boarding_pass(image_path, expected):
    """
    Evaluate OCR extraction for a single boarding pass image.

    Returns:
        dict with field-by-field results and overall accuracy
    """
    result = {
        "image": image_path,
        "fields": {},
        "total_expected": 0,
        "total_matched": 0,
        "accuracy": 0.0,
        "errors": []
    }

    try:
        # Get OCR reader
        reader = get_ocr_reader()

        # Run OCR
        print(f"\n  Running OCR on {os.path.basename(image_path)}...")
        ocr_results = reader.readtext(image_path)

        if not ocr_results:
            result["errors"].append("No text detected in image")
            return result

        # Extract text segments
        ocr_text_list = [text[1] for text in ocr_results]
        print(f"    Extracted {len(ocr_text_list)} text segments")

        # Extract fields
        extracted = extract_boarding_pass_fields(ocr_text_list)

        # Compare each expected field
        fields_to_check = [
            "flight_number", "passenger_name", "origin", "destination",
            "date", "boarding_time", "departure_time", "gate", "seat", "class"
        ]

        for field in fields_to_check:
            exp_value = expected.get(field)
            if exp_value is None:
                continue

            result["total_expected"] += 1
            ext_value = extracted.get(field)

            is_match, score = field_matches(ext_value, exp_value)

            result["fields"][field] = {
                "expected": exp_value,
                "extracted": ext_value,
                "match": is_match,
                "score": score
            }

            if is_match:
                result["total_matched"] += 1
                status = "[OK]"
            else:
                status = "[X]"

            print(f"    {status} {field}: expected '{exp_value}', got '{ext_value}'")

        # Calculate overall accuracy
        if result["total_expected"] > 0:
            result["accuracy"] = result["total_matched"] / result["total_expected"] * 100

        print(f"    Accuracy: {result['accuracy']:.1f}% ({result['total_matched']}/{result['total_expected']})")

    except Exception as e:
        result["errors"].append(str(e))
        print(f"    [ERROR] {e}")

    return result


def run_evaluation():
    """Run evaluation on all boarding pass samples."""
    print("\n" + "=" * 60)
    print("BOARDING PASS OCR EVALUATION")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load ground truth
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"\n[ERROR] Ground truth file not found: {GROUND_TRUTH_FILE}")
        return None

    with open(GROUND_TRUTH_FILE, 'r') as f:
        ground_truth = json.load(f)

    samples = ground_truth.get("samples", [])
    print(f"\nFound {len(samples)} test samples")

    all_results = []
    total_accuracy = 0

    for i, sample in enumerate(samples, 1):
        print(f"\n{'='*60}")
        print(f"SAMPLE {i}: {sample['description']}")
        print("=" * 60)

        image_path = os.path.join(SAMPLES_DIR, sample["filename"])

        if not os.path.exists(image_path):
            print(f"  [ERROR] Image not found: {image_path}")
            continue

        result = evaluate_single_boarding_pass(image_path, sample["expected"])
        result["sample_id"] = i
        result["description"] = sample["description"]
        all_results.append(result)
        total_accuracy += result["accuracy"]

    # Calculate summary
    avg_accuracy = total_accuracy / len(all_results) if all_results else 0

    # Summary by field
    field_stats = {}
    for result in all_results:
        for field, data in result["fields"].items():
            if field not in field_stats:
                field_stats[field] = {"total": 0, "matched": 0}
            field_stats[field]["total"] += 1
            if data["match"]:
                field_stats[field]["matched"] += 1

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    print(f"\n  Overall Accuracy: {avg_accuracy:.1f}%")
    print(f"  Samples Tested: {len(all_results)}")

    print("\n  Field-by-Field Accuracy:")
    for field, stats in sorted(field_stats.items()):
        if stats["total"] > 0:
            acc = stats["matched"] / stats["total"] * 100
            print(f"    {field:20}: {acc:5.1f}% ({stats['matched']}/{stats['total']})")

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(RESULTS_DIR, f"boarding_pass_eval_{timestamp}.json")

    report = {
        "metadata": {
            "date": datetime.now().isoformat(),
            "samples_tested": len(all_results),
            "overall_accuracy": avg_accuracy
        },
        "field_accuracy": {
            field: (stats["matched"] / stats["total"] * 100 if stats["total"] > 0 else 0)
            for field, stats in field_stats.items()
        },
        "detailed_results": all_results
    }

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n  Report saved: {report_path}")

    return report


if __name__ == "__main__":
    run_evaluation()
