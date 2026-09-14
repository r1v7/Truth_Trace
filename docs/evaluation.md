# Measuring the comparison engine

## Why this exists

"The system detects contradictions" is a claim, not a result. This directory is how the
claim gets a number attached to it — and how a change that fixes one case while breaking
three others becomes visible instead of invisible.

## Running it

```bash
docker compose run --rm --no-deps --entrypoint sh api -c "python -m evaluation.run_eval"
```

Options: `--errors` lists every wrong prediction with both claims; `--sweep` re-runs the
whole set across a range of link thresholds.

The dataset is `backend/evaluation/dataset.json`: 42 claim pairs, each labelled `match`,
`possible_conflict`, `unclear` or `missing` by hand, covering time, location, people and
negation differences as well as paraphrases and unrelated claims.

## Current result

Lexical backend, link threshold 0.55:

| Label | Precision | Recall | n |
| --- | --- | --- | --- |
| match | 1.00 | 1.00 | 12 |
| possible_conflict | 1.00 | 1.00 | 18 |
| unclear | 1.00 | 1.00 | 6 |
| missing | 1.00 | 1.00 | 6 |

Accuracy 42/42, and the correct field is named on every conflict.

## Read that number carefully

**42/42 is not an accuracy estimate for real statements.** The set is small, it was
written by one person, and the engine's rules were fixed while looking at its failures —
so the engine has effectively been fitted to it. What this result honestly supports is:

- the engine handles the scenarios the project brief describes, and
- a future change that breaks one of them will be caught.

What it does not support is any statement of the form "Truth Trace is 100% accurate."
For that you would need statements the engine's authors never saw, labelled by someone
who is not the person who wrote the rules.

The threshold sweep is more reassuring than the headline number: accuracy stays at 100%
for every link threshold from 0.30 to 0.60, so 0.55 is not a lucky value. Above 0.65,
conflict recall falls — contradictions stop being linked at all, which is the failure
mode to watch.

## The four bugs this found

Every one of these passed the unit tests and would have shipped:

1. **Irregular verbs were invisible.** Stemming only handled `-ed`/`-ing`, so `met`,
   `went`, `saw` and `drove` — the verbs statements are actually made of — carried no
   action signal, and pairs like "I met him at 7:30 PM" / "I met him at 10:00 PM" were
   never linked. The time contradiction was never reported.
2. **Names at the start of a sentence were dropped.** "Faisal drove me" and "Nasser drove
   me" compared as a *match*, because the person extractor skipped the first word of every
   sentence to avoid capitalised sentence starters.
3. **"I am not sure" read as a denial.** Any hedged statement containing "not sure" was
   reported as a negation contradiction.
4. **A differing location blocked linking.** "I parked in the parking lot" / "I parked in
   the street" scored just under the threshold and came back as two unrelated claims,
   so the location conflict was never raised.

## Adding to the dataset

Label first, run second. If a label looks wrong after seeing the engine's answer, the
honest fix is to argue for it in the `note` field or leave it — editing labels to match
the output turns the evaluation into a mirror.

Good additions are cases the engine is likely to get wrong: relative times ("an hour
later"), dates as well as clock times, ranges ("between eight and nine"), plural subjects,
and claims where the same words describe genuinely different events.

## Before real deployment

- Have someone who did not write the rules label a fresh set from real interview text.
- Measure precision and recall separately per field (time, location, person, negation) —
  the aggregate hides which extractor is weak.
- Only after that, consider showing a numeric score to investigators, and even then label
  it as a similarity score rather than a confidence percentage.
