from pathlib import Path

SUPERSONIC_VERSION = "latest"

SUPERSONIC_CDN = f"https://unpkg.com/supersonic-scsynth@{SUPERSONIC_VERSION}"
SUPERSONIC_CORE_CDN = f"https://unpkg.com/supersonic-scsynth-core@{SUPERSONIC_VERSION}/"
SUPERSONIC_SYNTHDEFS_CDN = f"https://unpkg.com/supersonic-scsynth-synthdefs@{SUPERSONIC_VERSION}/synthdefs/"
SUPERSONIC_SAMPLES_CDN = f"https://unpkg.com/supersonic-scsynth-samples@{SUPERSONIC_VERSION}/samples/"

SCHEDULER_JS_PATH = Path(__file__).parent / "scheduler.js"
DRAW_JS_PATH = Path(__file__).parent / "draw.js"


def supersonic_import_script():
    return (
        f'<script type="module">\n'
        f'import {{ SuperSonic }} from "{SUPERSONIC_CDN}";\n'
        f'globalThis.SuperSonic = SuperSonic;\n'
        f'globalThis.__supersonicReady = true;\n'
        f'</script>\n'
    )


def supersonic_config_json():
    return {
        "baseURL": f"{SUPERSONIC_CDN}/dist/",
        "coreBaseURL": SUPERSONIC_CORE_CDN,
        "synthdefBaseURL": SUPERSONIC_SYNTHDEFS_CDN,
        "sampleBaseURL": SUPERSONIC_SAMPLES_CDN,
    }
