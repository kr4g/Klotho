from pathlib import Path

# Pinned: boot behavior now depends on constructor options (scsynthOptions
# below), so the engine must not change under saved notebooks mid-course.
SUPERSONIC_VERSION = "0.71.0"

SUPERSONIC_CDN = f"https://unpkg.com/supersonic-scsynth@{SUPERSONIC_VERSION}"
SUPERSONIC_CORE_CDN = f"https://unpkg.com/supersonic-scsynth-core@{SUPERSONIC_VERSION}/"
SUPERSONIC_SYNTHDEFS_CDN = f"https://unpkg.com/supersonic-scsynth-synthdefs@{SUPERSONIC_VERSION}/synthdefs/"
SUPERSONIC_SAMPLES_CDN = f"https://unpkg.com/supersonic-scsynth-samples@{SUPERSONIC_VERSION}/samples/"

DRAW_JS_PATH = Path(__file__).parent / "draw.js"

# Output buses 0/1 are the audible master pair; 2..31 are stem-tap pairs used
# only during a stems recording (the widget's capture node reads them; the
# speaker path is clamped to the hardware's 2 channels, so they are silent
# otherwise). scsynth places input buses right after outputs, so the private
# bus space starts at numOutput + numInput = 34; the JS schedulers allocate
# track/FX buses from FIRST_PRIVATE_BUS = 48 (see scheduler_core.js), which
# must stay >= that hardware span.
# Private audio buses. Raised 256 -> 1024 for multichannel output: one bus
# channel per speaker means a 24-speaker track costs 24 channels per bus, and
# 256 channels leave only 208 above FIRST_PRIVATE_BUS = 48 -- room for exactly
# one spatial track with one insert. 1024 leaves 976, about 13 spatial tracks
# with two inserts each. The raise is UNCONDITIONAL, so every fresh page is
# spatial-capable: a per-page opt-in would mean the first spatial play() on a
# page whose engine already booted non-spatial raises "reload the notebook",
# which in a Colab session is the moment you least want to lose state. Cost is
# one contiguous float array, one block per bus: 1024 x 128 samples x 4 B =
# 512 KB, against the ~90 MB/widget a SuperSonic widget already costs. (128,
# not 64: SuperSonic refuses any bufLength but 128 -- "scsynthOptions.
# bufLength must be 128 (WebAudio API constraint)" -- so the block size is
# not ours to choose and the arithmetic cannot use a smaller one.)
#
# numOutputBusChannels stays 32 and must not follow: the speaker array lives on
# PRIVATE buses, hardware channels above 0/1 are inaudible in the browser
# (the speaker path is clamped to 2), 2..31 are already spoken for as stem-tap
# pairs, and raising it would push the hardware span above FIRST_PRIVATE_BUS.
# 32 also already covers the widest hardware mirror the design asks for
# (channels 2..31 = 30 speakers).
SCSYNTH_NUM_OUTPUT_CHANNELS = 32
SCSYNTH_NUM_AUDIO_BUSES = 1024

# What supersonic-scsynth boots with when NOTHING is passed for it. Klotho
# passed no scsynthOptions at all before 10.16, so an engine started by a
# saved output older than that is running on these -- which is what
# scheduler_score.js must assume when a page has no bootConfig stash to read.
# Read out of the pinned dist bundle itself
# (https://unpkg.com/supersonic-scsynth@0.71.0/dist/supersonic.js, defaults
# object: numAudioBusChannels:128, maxWireBufs:64, bufLength:128), so they are
# coupled to SUPERSONIC_VERSION and must be re-read when it moves.
SUPERSONIC_DEFAULT_NUM_AUDIO_BUSES = 128
SUPERSONIC_DEFAULT_MAX_WIRE_BUFS = 64
# Not an option at all: SuperSonic refuses any other value.
SUPERSONIC_BLOCK_SIZE = 128


def supersonic_config():
    return {
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
        "scsynthOptions": {
            "numOutputBusChannels": SCSYNTH_NUM_OUTPUT_CHANNELS,
            "numAudioBusChannels": SCSYNTH_NUM_AUDIO_BUSES,
        },
    }
