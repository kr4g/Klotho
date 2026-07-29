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
SCSYNTH_NUM_OUTPUT_CHANNELS = 32
SCSYNTH_NUM_AUDIO_BUSES = 256


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
