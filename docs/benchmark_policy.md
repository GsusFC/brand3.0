# Benchmark Policy

## Purpose

Brand3 needs two different benchmark types:

- `exploratory`: used to discover failures, edge cases, and new profile ideas
- `canonical`: used to measure regressions and guide calibration decisions

They are not interchangeable.

## Benchmark Types

### Exploratory

Use this when:

- testing a new niche or profile idea
- checking whether the classifier is directionally correct
- probing weak parts of scraping or scoring

Properties:

- can include messy or ambiguous companies
- can include unstable domains
- can include partial labels
- does not block code changes

### Canonical

Use this when:

- deciding whether a calibration change is better or worse
- protecting against scoring regressions
- comparing profile variants over time

Properties:

- only manually curated companies
- every company has a written rationale
- every label is reviewable
- every domain must be stable and accessible

## Inclusion Rules For Canonical

A company can enter the canonical benchmark only if all of these are true:

1. The main domain is live and returns real brand content, not parking, placeholder, or SEO spam.
2. The brand identity is unambiguous.
3. The company fits one primary profile clearly enough to justify it in writing.
4. The company has enough public signal for scoring:
   - working homepage
   - crawlable core pages
   - search/indexed references or news
5. The current website state is internally consistent across main pages.
6. The expected label is reviewed by at least one human after first proposal.

## Exclusion Rules

Do not include a company in canonical if any of these are true:

- parked or resold domain
- mixed brand / domain identity
- website is mostly inaccessible to collectors
- duplicate company under multiple domains
- company has pivoted and public footprint is inconsistent
- label depends on private knowledge not visible in public artifacts

These companies can stay in exploratory under a flag like `invalid_web_state`, `ambiguous_brand`, or `insufficient_public_signal`.

## Target Size

Do not start too large.

Recommended v1 size:

- `15-20` companies total
- `4-6` companies per active profile

Current active profiles:

- `frontier_ai`
- `enterprise_ai`
- `physical_ai`
- `base`

## Distribution Rules

Each profile should include three case types:

- `clear positives`: obvious examples the classifier should get right
- `near-boundary cases`: plausible but confusable examples
- `negative controls`: companies that should not be assigned to that profile

Suggested initial mix:

- `frontier_ai`: 5 companies
- `enterprise_ai`: 5 companies
- `physical_ai`: 4 companies
- `base`: 4 companies

That yields `18` total.

## Required Fields

Each benchmark entry should contain:

- `brand_name`
- `url`
- `expected_niche`
- `expected_subtype`
- `notes`
- `inclusion_reason`
- `review_status`
- `signal_quality`

Recommended extra fields:

- `known_risks`
- `reviewer`
- `last_verified_at`

## Review Status

Use only these values:

- `draft`
- `reviewed`
- `approved`
- `excluded`

Only `approved` entries belong in canonical.

## Signal Quality

Use only these values:

- `high`
- `medium`
- `low`

Canonical should usually be `high` or `medium`.

## Evaluation Criteria

Canonical benchmark review should score three things separately:

1. `classification`
   - did the system predict the right profile?
   - did it predict the right subtype?

2. `score shape`
   - does the score distribution feel directionally right?
   - do the strongest and weakest dimensions make sense?

3. `explanation quality`
   - do the evidence and dimensions justify the result?
   - if a human disagrees, is the disagreement explainable?

## Promotion Rule

An exploratory set becomes canonical only if:

1. every company passes inclusion rules
2. every company has written rationale
3. every company has `review_status = approved`
4. no known invalid domains remain in the set
5. the set has balanced profile coverage

## Current Repo Convention

Use:

- `examples/startup_benchmark.json` for exploratory work
- `examples/canonical_benchmark.template.json` as the canonical schema template

Do not treat `startup_benchmark.json` as canonical by default.
