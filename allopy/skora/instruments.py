from enum import Enum, EnumMeta

class PFIELDS(Enum):
    # STD = {
    # }

    SineEnv = {
        'start'      : 0,
        'dur'        : 1,
        'synthName'  : 'SineEnv',
        'amplitude'  : 0.45,
        'frequency'  : 440,
        'attackTime' : 0.01,
        'releaseTime': 0.1,
        'pan'        : 0.0,
    }

    # OscAM = {}

    PluckedString = {
        'start'      : 0,
        'dur'        : 1,
        'synthName'  : 'PluckedString',
        'amplitude'  : 0.45,
        'frequency'  : 440,
        'attackTime' : 0.01,
        'releaseTime': 0.1,
        'sustain'    : 0.5,
        'Pan1'       : 0.0,
        'Pan2'       : 0.0,
        'PanRise'    : 0.0,
    }