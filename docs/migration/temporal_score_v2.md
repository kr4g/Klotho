# Migration: Temporal + Score API v2

This document covers the coordinated refactor of Klotho's temporal
classes (``TemporalUnit``, ``TemporalUnitSequence``, ``TemporalBlock``,
``CompositionalUnit``) and the ``Score`` class introduced alongside
Klotho 7.0.

## Design shift in one sentence

**Temporal units are now _materials_ whose time (start, duration) is
immutable outside a ``Score``.  ``Score`` owns the arrangement: where
an item lives on the timeline and what its total duration is.**

## The three coordinated changes

1. **Offsets are private.** Every temporal class (UT, UTS, BT, UC)
   always starts at time ``0`` outside a Score.  ``unit.offset`` is
   gone as both a constructor kwarg and a property.  Read placement
   via the new read-only ``unit.start`` property.  Placement itself is
   assigned by Score via ``add(at=)`` / ``add(after=)`` / ``add(before=)``.
2. **Duration is immutable outside a Score.**  ``set_duration`` has
   been removed from all temporal classes.  The only way to change a
   unit's total duration is through the owning
   :class:`~klotho.thetos.composition.score.ScoreItem` returned by
   ``Score.add``.
3. **``Score`` holds items, not events.**  ``Score.add`` copies the
   submitted unit (always), auto-promotes bare ``TemporalUnit`` nodes
   to ``CompositionalUnit``, records placement, and returns a
   ``ScoreItem`` wrapper.  Lowering to SuperCollider events is
   deferred: ``Score.play`` as a method is gone; use the universal
   ``play(score)`` dispatcher instead.

## Before / after syntax

| Before                                    | After                                                      |
|-------------------------------------------|------------------------------------------------------------|
| `UT(..., offset=2.5)`                     | `score.add(UT(...), at=2.5)`                               |
| `ut.offset = 2.5`                         | `score.add(ut, at=2.5)`                                    |
| `ut.offset`                               | `ut.start` _(always 0 outside a Score)_                    |
| `ut.set_duration(8.0)`                    | `score.add(ut, name='x'); score['x'].set_duration(8.0)`    |
| `uts.set_duration(30.0)`                  | `score['seq'].set_duration(30.0)` _(after add)_            |
| `score.play()`                            | `play(score)` _(universal dispatcher)_                     |
| `Score().add(uc)` _returns Score_         | `Score().add(uc, name='a')` _returns ScoreItem_            |
| `len(score._event_heap)`                  | `len(score)` _(item count)_                                |
| `score.total_events`                      | removed; call `convert_score_to_sc_events(score)`          |
| `score._build_meta()`                     | `convert_score_to_sc_events(score)['meta']`                |
| `score._build_control_data()`             | `convert_score_to_sc_events(score)['control_data']`        |
| `score._drain_events()`                   | `convert_score_to_sc_events(score)['events']`              |

## New placement kwargs

```python
from klotho.thetos.composition.score import Score
from klotho.thetos import CompositionalUnit as UC

intro = UC(tempus='4/4', prolatio=(1,)*4, bpm=120)
verse = UC(tempus='4/4', prolatio=(1,)*8, bpm=120)
pre   = UC(tempus='2/4', prolatio=(1,)*2, bpm=120)

s = Score()
s.add(intro, name='intro')                      # at=0 (default)
s.add(verse, name='verse', after='intro')       # verse.start = intro.end
s.add(pre,   name='pre',   before='intro')      # pre.end   = intro.start
s.add(UC(...), name='coda', at=30.0)            # absolute time
s.add(UC(...), name='echo', at='verse')         # matches verse.start
```

Mutually exclusive: only one of ``at``, ``after``, ``before`` per
``add()`` call (enforced with a ``ValueError``).

Convenience methods:

```python
s.append(uc, name='tail')     # appends at current latest end
s.prepend(uc, name='head')    # prepends at 0; shifts all existing items right
```

## ScoreItem mutation

``Score.add(unit)`` returns a ``ScoreItem`` (also retrievable via
``score[name]``).  The item owns a copy of the unit; mutations through
the item do not affect any external reference.

```python
item = s.add(uc, name='verse')
item.set_duration(8.0)                          # scales owned UC's bpm
item.stretch(1.25)                              # same, as a multiplier
item.set_duration(8.0, ripple=True)             # shifts everything at/after
                                                #  item's current end by the delta
item.freeze()                                   # subsequent set_duration / stretch
                                                #  raises RuntimeError
```

Attribute access on a ``ScoreItem`` falls through to the owned unit,
so you can keep calling UC-level methods through the handle:

```python
item.set_pfields(item.leaf_nodes, freq=440)
item.apply_envelope(env, 'amp', node=item.rt.root)
for leaf in item.leaf_nodes: ...
```

## Copy-on-add and ownership

```python
uc = UC(..., pfields={'amp': 0.5})
s  = Score()
s.add(uc, name='a')

uc.set_pfields(uc.rt.leaf_nodes[0], amp=0.999)    # external mutation
assert s['a'].unit.get_pfield(...) == 0.5          # score's copy is unchanged

s['a'].set_pfields(s['a'].leaf_nodes[0], amp=0.1)  # score mutation
assert uc.get_pfield(...) == 0.5                   # external ref is unchanged
```

The same rule applies to duration changes, envelope applications, slurs,
etc.  There is no ``consume=True`` or ownership-transfer path: every
``add`` always copies.

## UT → UC auto-promotion

Any bare :class:`~klotho.chronos.TemporalUnit` submitted to
``Score.add`` (directly or nested inside a ``TemporalUnitSequence`` /
``TemporalBlock``) is promoted to a
:class:`~klotho.thetos.composition.CompositionalUnit` on entry.  The
promoted UC has no pfields or instruments by default; assign them
through the returned ``ScoreItem``.

```python
item = s.add(UT(...), name='drums')
item.set_instrument(item.rt.root, KickInstrument())
item.set_pfields(item.leaf_nodes, amp=0.6)
```

## Playback dispatch

``Score.play`` is removed.  Render through the universal
:func:`klotho.play` function:

```python
from klotho import play

play(score)                 # renders the SuperSonic widget
play(score, ring_time=10)   # ring-out seconds after playback ends
```

Under the hood, the dispatcher calls
:func:`~klotho.utils.playback.supersonic.converters.convert_score_to_sc_events`
to lower items to the SC event payload, then hands it to
``SuperSonicEngine``.

## ``Score.write`` (JSON export)

``write`` remains a method on ``Score`` (there is no universal
``write(obj, path)`` function yet).  Its contract is unchanged:

```python
score.write('out.json', start_time=0.0, time_scale=1.0)
```

Internally it now lowers via ``convert_score_to_sc_events`` and
applies the shift/scale to the returned payload.

## Porting pre-Score workflows

### "I built and stretched a UTS, then played it"

```python
# Before
uts = UTS(ut_seq=[ut1, ut2, ut3])
uts.set_duration(30.0)
uts.offset = 5.0
# (and then later some eager lowering path)

# After
from klotho import play
from klotho.thetos.composition.score import Score

s = Score()
item = s.add(UTS(ut_seq=[uc1, uc2, uc3]), name='seq', at=5.0)
item.set_duration(30.0)
play(s)
```

### "I had a bunch of UCs placed at specific offsets"

```python
# Before
uc_a = UC(..., offset=0.0)
uc_b = UC(..., offset=uc_a.duration)
uc_c = UC(..., offset=uc_a.duration + uc_b.duration)

# After
s = Score()
s.add(UC(...), name='a')
s.add(UC(...), name='b', after='a')
s.add(UC(...), name='c', after='b')
# or equivalently:
# s.append(UC(...), name='a')
# s.append(UC(...), name='b')
# s.append(UC(...), name='c')
```

### "I want to shorten one clip and have everything after slide left"

```python
# After
s['a'].set_duration(s['a'].duration * 0.5, ripple=True)
```

## Test authoring notes

* Prefer ``score.add(unit, at=...)`` over constructing with ``offset``.
* Assert on ``unit.start`` / ``item.start`` rather than ``unit.offset``.
* To test duration changes, go through ``ScoreItem.set_duration``.
* To inspect the lowered event stream, call
  ``convert_score_to_sc_events(score)`` instead of reading internal
  ``_event_heap`` / ``_control_descriptors`` / ``_total_events``
  attributes — those are gone.

## What remains unchanged

* The rhythm-tree layer (``RhythmTree``, ``Meas``, proportions).
* Per-leaf UC mutation APIs (``set_pfields``, ``set_mfields``,
  ``set_instrument``, ``apply_envelope``, ``apply_slur``,
  ``make_rest``, ``subdivide``).
* The SuperCollider event contract delivered to ``SuperSonicEngine`` —
  ``{events, meta, control_data}`` payload shape is identical.  This
  keeps a future Rust-based lowering backend drop-in compatible.
* ``Score.from_ensemble``, ``Score.track``, ``Score.clear``,
  ``Score.tracks``.
