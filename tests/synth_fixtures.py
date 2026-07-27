"""SynthDef-backed stand-ins for the removed ToneInstrument preset factories.

The structural test suites (API equivalence, UC/PT regression, selector
parity) used ToneInstrument's named factories purely as *distinct
instruments with default pfields* — nothing Tone.js-specific. This module
provides the same construction surface (``SynthFixtures.Kick()``,
``SynthFixtures.Ride(decay=0.2)``, ``SynthFixtures.Kick('kick_punchy',
punch=16)``) on top of ``SynthDefInstrument`` so those suites keep
exercising per-node instrument assignment, Pattern distribution, and
pfield defaults with the SuperSonic-only backend.
"""
from klotho.thetos import SynthDefInstrument


def _factory(default_name):
    def make(name=None, **pfields):
        base = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
        base.update(pfields)
        return SynthDefInstrument(name=name or default_name, defName='kl_tri',
                                  pfields=base)
    return staticmethod(make)


class SynthFixtures:
    Kick = _factory('Kick')
    Snare = _factory('Snare')
    HatClosed = _factory('HatClosed')
    HatOpen = _factory('HatOpen')
    TomHigh = _factory('TomHigh')
    TomMid = _factory('TomMid')
    TomLow = _factory('TomLow')
    Ride = _factory('Ride')
    Kalimba = _factory('Kalimba')
    Bassy = _factory('Bassy')
