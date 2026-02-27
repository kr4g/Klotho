import math
from klotho.dynatos.dynamics import freq_amp_scale, ampdb


DEFAULT_AMP = 0.5


def single_voice_amplitude(freq, target_amp=None):
    if target_amp is None:
        target_amp = DEFAULT_AMP
    scaled = freq_amp_scale(freq, ampdb(target_amp))
    return min(1.0, max(0.05, target_amp * (scaled / max(0.01, target_amp))))


def compute_voice_amplitudes(freqs, target_amp=None):
    if target_amp is None:
        target_amp = DEFAULT_AMP
    n = len(freqs)
    if n == 0:
        return []
    if n == 1:
        return [single_voice_amplitude(freqs[0], target_amp)]

    weights = []
    for freq in freqs:
        w = freq_amp_scale(freq, ampdb(target_amp))
        weights.append(max(0.01, w))

    total_w = sum(weights)
    normalized = [w / total_w for w in weights]

    headroom = max(1.0, math.sqrt(n))
    amps = [(target_amp * nw * n) / headroom for nw in normalized]

    return [min(1.0, max(0.05, a)) for a in amps]
