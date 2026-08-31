# Tests — where expected values come from

A test proves nothing if its expected value was produced by the code under
test. The failure is silent and total: the assertion passes for any behaviour,
wrong included, because both sides moved together when it was written.

This file exists because that happened here, and because the consequence is
easy to misread. On 2026-08-29 a hostile pass found 48 real defects under a
fully green suite of 7,000 tests. The tests were not fake. They were measuring
the wrong thing.

## Regression oracles vs correctness oracles

**A regression oracle** is captured from Klotho's own output at some past
moment. It answers *"did behaviour change?"* — reliably, and that is worth
having. It can never answer *"is behaviour right?"*, because when it was
captured, the values and the code came from the same place.

Nearly everything here is one: `expected_trees.json`, `expected_uc_pt.json`,
`fixtures/parity/*.json`, `fixtures/lowering_equivalence_golden.json`.

**A correctness oracle** comes from outside the codebase, so agreement with it
means something. There are two kinds available:

- **Published figures.** `fixtures/haddad_figures.json` holds Haddad's printed
  OpenMusic s-expressions, extracted from the thesis by
  `scripts/capture_haddad_figures.py`, which never imports `klotho`. See
  `test_haddad_figure_conformance.py`.
- **Properties and invariants.** No literal value at all — `sum(|durations|)
  == meas * span`, round-trips, identities. Derivable from the *definition*,
  so there is nothing an implementation can do to make one agree falsely.

When you report the suite, report both. *"7,362 green"* is a statement about
regression only.

### How to say it, in plain English

Earlier versions of this file asked for a close line reading *"correctness
coverage is F figures and P invariants"*. That was jargon, and the project
owner said so: the letters meant nothing to the person the report is for, and
`P` was quoted with three different values in one document because nobody had
written down how to count it. **Do not use the letters.** Say it plainly, and
name the files so the numbers can be checked:

> 7,661 tests pass. 34 of those check correctness against something outside
> Klotho -- 5 against Haddad's printed figures
> (`test_haddad_figure_conformance.py`), 29 against rules that hold by
> definition (`test_rt_operator_composition_laws.py`,
> `test_container_algebra_properties.py`). The rest check that behaviour has
> not changed.

Both numbers are countable from named files, which is the whole point: a
figure you can `grep` cannot drift, and a classifier over test source can --
one was wrong five times running before it was abandoned.

## The four provenance tiers

Every expected value should be traceable to one of these. Prefer the top.

1. **Property** — no literal. Strongest, and cheapest to trust.
2. **Published figure** — cite it (`fig. 2.14`, thesis p280).
3. **Hand-computed** — say who and when.
4. **Captured golden** — from a *reference build*, never this tree. Commit it
   **alone**, so the diff is reviewable in isolation, and read the diff.

## Two rules

**An agent may never author a literal expected value for code it wrote in the
same session.** It comes from a figure, a property, a pre-change capture, or a
human. This is the rule that everything else here is enforcement for.

**Commit the test first, alone, watched red. Then the implementation.** Red
before green is already the discipline; committing in that order is what makes
it *auditable* afterwards. Git then proves the expected value could not have
come from the implementation — which no amount of prose can.

As of 2026-08-30, 133 of 139 test files added since February were committed in
the same commit as the source they test. That is not proof any of them is
circular — a disciplined author produces the same signature — but it does mean
git cannot tell, and unauditable is where this went wrong.

## The lock

Four paths can overwrite an oracle. All four refuse without
`KLOTHO_ALLOW_REGEN=1`, which an agent may not set (`_oracle_lock.py`). The
capture scripts refuse a second time if `klotho` resolved to this repository.
`test_oracle_integrity.py` polices it, including finding a *new* capture script
added later without a guard.

None of that judges whether a regeneration was honest. It stops an oracle being
overwritten other than by a deliberate human act.
