from pathlib import Path

SUPERSONIC_VERSION = "latest"

SUPERSONIC_CDN = f"https://unpkg.com/supersonic-scsynth@{SUPERSONIC_VERSION}"
SUPERSONIC_CORE_CDN = f"https://unpkg.com/supersonic-scsynth-core@{SUPERSONIC_VERSION}/"
SUPERSONIC_SYNTHDEFS_CDN = f"https://unpkg.com/supersonic-scsynth-synthdefs@{SUPERSONIC_VERSION}/synthdefs/"
SUPERSONIC_SAMPLES_CDN = f"https://unpkg.com/supersonic-scsynth-samples@{SUPERSONIC_VERSION}/samples/"

DRAW_JS_PATH = Path(__file__).parent / "draw.js"


def supersonic_config():
    return {
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
    }
