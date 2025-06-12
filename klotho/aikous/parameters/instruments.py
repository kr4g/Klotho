from enum import Enum
from klotho.utils.data_structures.dictionaries import SafeDict

class PFIELDS(Enum):
    def __call__(self):
        # return SafeDict(self.value.copy())
        return self.value.copy()

    SineEnv = SafeDict({
        'start'      : 0,
        'dur'        : 1,
        'synthName'  : 'SineEnv',
        'amplitude'  : 0.45,
        'frequency'  : 440,
        'attackTime' : 0.01,
        'releaseTime': 0.1,
        'pan'        : 0.0,
    })

    Vib = SafeDict({
        'start'      : 0,
        'dur'        : 1,
        'synthName'  : 'Vib',
        'amplitude'  : 0.45,
        'frequency'  : 440,
        'attackTime' : 0.01,
        'releaseTime': 0.1,
        'sustain'    : 0.5,
        'curve'      : 4.0,
        'pan'        : 0.0,
        'table'      : 0,
        'vibRate1'   : 3.5,
        'vibRate2'   : 5.8,
        'vibRise'    : 0.5,
        'vibDepth'   : 0.005,     
    })

    FMWT = SafeDict({
        'start'        : 0,
        'dur'          : 1,
        'synthName'    : 'FMWT',
        'frequency'    : 440,
        'amplitude'    : 0.45,
        'attackTime'   : 0.01,
        'releaseTime'  : 0.1,
        'sustain'      : 0.5,
        'idx1'         : 0.01,
        'idx2'         : 7,
        'idx3'         : 5,
        'carMul'       : 1,
        'modMul'       : 1.0007,
        'vibRate1'     : 0.01,
        'vibRate2'     : 0.5,
        'vibRise'      : 0,
        'vibDepth'     : 0,
        'pan'          : 0.0,
        'table'        : 0,
        'reverberation': 0.0,
    })

    OscTrm = SafeDict({
        'start'      : 0,
        'dur'        : 1,
        'synthName'  : 'OscTrm',
        'amplitude'  : 0.45,
        'frequency'  : 440,
        'attackTime' : 0.01,
        'releaseTime': 0.1,
        'sustain'    : 0.5,
        'curve'      : 4.0,
        'pan'        : 0.0,
        'table'      : 0,
        'trm1'       : 3.5,
        'trm2'       : 5.8,
        'trmRise'    : 0.5,
        'trmDepth'   : 0.1,
    })

    OscAM = SafeDict({
        'start'        : 0,
        'dur'          : 1,
        'synthName'    : 'OscAM',
        'amplitude'    : 0.45,
        'frequency'    : 440,
        'attackTime'   : 0.01,
        'releaseTime'  : 0.1,
        'sustain'      : 0.5,
        'pan'          : 0.0,
        'amFunc'       : 0.0,
        'am1'          : 0.75,
        'am2'          : 0.75,
        'amRise'       : 0.75,
        'amRatio'      : 0.75,
        'reverberation': 0.0,
        'visualMode'   : 0.0,
    })

    AddSyn = SafeDict({
        'start'        : 0,
        'dur'          : 1,
        'synthName'    : 'AddSyn',
        'amp'          : 0.45,
        'frequency'    : 440,
        'ampStri'      : 0.5,
        'attackStri'   : 0.1,
        'releaseStri'  : 0.1,
        'sustainStri'  : 0.8,
        'ampLow'       : 0.5,
        'attackLow'    : 0.001,
        'releaseLow'   : 0.1,
        'sustainLow'   : 0.8,
        'ampUp'        : 0.6,
        'attackUp'     : 0.01,
        'releaseUp'    : 0.075,
        'sustainUp'    : 0.9,
        'freqStri1'    : 1.0,
        'freqStri2'    : 2.001,
        'freqStri3'    : 3.0,
        'freqLow1'     : 4.009,
        'freqLow2'     : 5.002,
        'freqUp1'      : 6.0,
        'freqUp2'      : 7.0,
        'freqUp3'      : 8.0,
        'freqUp4'      : 9.0,
        'pan'          : 0.0,
        'reverberation': 0.0,
    })

    PluckedString = SafeDict({
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
    })
    