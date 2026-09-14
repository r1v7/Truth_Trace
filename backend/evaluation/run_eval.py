"""Measure the comparison engine against hand-labelled claim pairs.

Run it before changing anything in app/analysis, and again after, so a change that
fixes one case but breaks three others is visible instead of invisible.

    python -m evaluation.run_eval
    python -m evaluation.run_eval --sweep          # link-threshold sweep
    python -m evaluation.run_eval --errors         # list every wrong prediction

What the numbers mean for this project:
  - recall on possible_conflict   how many real contradictions the investigator is shown.
  - precision on possible_conflict how much of what they are shown is worth their time.
Missing a contradiction is the more serious failure; a false alarm costs a review.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from app.analysis.engine import ClaimInput, compare
from app.core.config import settings

DATASET = Path(__file__).with_name("dataset.json")
LABELS = ["match", "possible_conflict", "unclear", "missing"]


def load_items() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))["items"]


def predict(a: str, b: str) -> tuple[str, str | None]:
    """Return the engine's verdict for one pair, as (label, field)."""
    results = compare([ClaimInput(1, a)], [ClaimInput(2, b)])
    if not results:
        return "missing", None
    top = results[0]
    # Two unlinked claims come back as two separate 'missing' rows - that is the
    # engine saying "these are not about the same thing".
    if top.finding_type.value == "missing":
        return "missing", None
    return top.finding_type.value, top.field.value


def evaluate(items: list[dict]) -> dict:
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    errors = []
    field_right = field_total = 0

    for item in items:
        predicted, field = predict(item["a"], item["b"])
        expected = item["expected"]
        confusion[expected][predicted] += 1

        if "field" in item:
            field_total += 1
            if predicted == expected and field == item["field"]:
                field_right += 1

        if predicted != expected:
            errors.append({**item, "predicted": predicted, "predicted_field": field})

    correct = sum(confusion[label][label] for label in LABELS)
    return {
        "total": len(items),
        "correct": correct,
        "accuracy": correct / len(items) if items else 0.0,
        "confusion": confusion,
        "errors": errors,
        "field_accuracy": field_right / field_total if field_total else None,
    }


def per_label(confusion) -> dict[str, dict[str, float]]:
    scores = {}
    for label in LABELS:
        tp = confusion[label][label]
        predicted_total = sum(confusion[other][label] for other in LABELS)
        actual_total = sum(confusion[label].values())
        precision = tp / predicted_total if predicted_total else 0.0
        recall = tp / actual_total if actual_total else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        scores[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": actual_total,
        }
    return scores


def print_report(result: dict, show_errors: bool) -> None:
    print(f"\nBackend: {settings.analyzer_backend}   "
          f"link threshold: {settings.similarity_link_threshold}")
    print(f"Accuracy: {result['correct']}/{result['total']} = {result['accuracy']:.1%}")
    if result["field_accuracy"] is not None:
        print(f"Correct field named on conflicts: {result['field_accuracy']:.1%}")

    print("\nPer label:")
    print(f"  {'label':<20}{'prec':>7}{'recall':>8}{'f1':>7}{'n':>5}")
    for label, s in per_label(result["confusion"]).items():
        print(f"  {label:<20}{s['precision']:>7.2f}{s['recall']:>8.2f}"
              f"{s['f1']:>7.2f}{s['support']:>5}")

    print("\nConfusion (rows = labelled, columns = predicted):")
    print(f"  {'':<20}" + "".join(f"{label[:9]:>11}" for label in LABELS))
    for expected in LABELS:
        row = "".join(f"{result['confusion'][expected][p]:>11}" for p in LABELS)
        print(f"  {expected:<20}{row}")

    if show_errors and result["errors"]:
        print(f"\n{len(result['errors'])} wrong predictions:")
        for e in result["errors"]:
            field = f" ({e['predicted_field']})" if e["predicted_field"] else ""
            print(f"  [{e['id']}] labelled {e['expected']}, predicted {e['predicted']}{field}")
            print(f"       A: {e['a']}")
            print(f"       B: {e['b']}")


def sweep(items: list[dict]) -> None:
    print("\nLink-threshold sweep (conflict recall is the one to protect):")
    print(f"  {'threshold':>10}{'accuracy':>10}{'conflict P':>12}{'conflict R':>12}")
    original = settings.similarity_link_threshold
    try:
        for step in range(30, 85, 5):
            settings.similarity_link_threshold = step / 100
            result = evaluate(items)
            scores = per_label(result["confusion"])["possible_conflict"]
            print(f"  {step / 100:>10.2f}{result['accuracy']:>10.1%}"
                  f"{scores['precision']:>12.2f}{scores['recall']:>12.2f}")
    finally:
        settings.similarity_link_threshold = original


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", action="store_true", help="try a range of link thresholds")
    parser.add_argument("--errors", action="store_true", help="list every wrong prediction")
    args = parser.parse_args()

    items = load_items()
    print_report(evaluate(items), show_errors=args.errors)
    if args.sweep:
        sweep(items)

    print(
        "\nThis set is small and written by hand. It catches regressions; it does not "
        "establish accuracy on real statements."
    )


if __name__ == "__main__":
    main()
