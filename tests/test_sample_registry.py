"""Runtime sample registry, WAV metadata parser, and fetch helpers."""
import io
import struct
import wave
import zipfile
from pathlib import Path

import pytest

from klotho.utils.playback.supersonic.samples import (
    register_sample, unregister_sample, registered_samples,
    clear_runtime_samples, sample_info, sample_bytes_b64, sample_names,
    sample_groups,
)
from klotho.utils.playback.supersonic._wav_meta import wav_metadata


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_runtime_samples()
    yield
    clear_runtime_samples()


def make_wav(channels=1, rate=44100, frames=500, width=2, seed=0):
    bio = io.BytesIO()
    with wave.open(bio, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(bytes([seed % 256]) * (frames * channels * width))
    return bio.getvalue()


def make_float_wav(rate=48000, frames=100, channels=1):
    data_size = frames * channels * 4
    hdr = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
    fmt = b'fmt ' + struct.pack('<IHHIIHH', 16, 3, channels, rate,
                                rate * channels * 4, channels * 4, 32)
    return hdr + fmt + b'data' + struct.pack('<I', data_size) + b'\x00' * data_size


class TestWavMetadata:
    def test_pcm16_stereo(self):
        m = wav_metadata(make_wav(channels=2, frames=1000))
        assert m['channels'] == 2
        assert m['sampleRate'] == 44100
        assert m['frames'] == 1000
        assert m['bitsPerSample'] == 16
        assert m['formatTag'] == 1
        assert m['duration'] == pytest.approx(1000 / 44100)

    def test_pcm24_mono(self):
        m = wav_metadata(make_wav(channels=1, width=3))
        assert m['channels'] == 1
        assert m['bitsPerSample'] == 24

    def test_float32(self):
        m = wav_metadata(make_float_wav())
        assert m['formatTag'] == 3
        assert m['frames'] == 100

    @pytest.mark.parametrize("blob, hint", [
        (b'FORM' + b'\x00' * 4 + b'AIFF' + b'\x00' * 32, 'AIFF'),
        (b'fLaC' + b'\x00' * 64, 'FLAC'),
        (b'OggS' + b'\x00' * 64, 'Ogg'),
        (b'ID3' + b'\x00' * 64, 'MP3'),
        (b'\xff\xfb' + b'\x00' * 64, 'MP3'),
        (b'not audio at all' + b'\x00' * 32, 'RIFF'),
    ])
    def test_friendly_rejections(self, blob, hint):
        with pytest.raises(ValueError, match=hint):
            wav_metadata(blob)

    def test_compressed_wav_rejected(self):
        data_size = 100
        hdr = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
        fmt = b'fmt ' + struct.pack('<IHHIIHH', 16, 0x0055, 1, 44100,
                                    44100, 1, 8)
        blob = hdr + fmt + b'data' + struct.pack('<I', data_size) + b'\x00' * data_size
        with pytest.raises(ValueError, match='MP3'):
            wav_metadata(blob)


class TestRegisterSample:
    def test_register_bytes_and_lookup(self):
        register_sample('my_kick', make_wav(channels=1), group='mine')
        assert sample_info('my_kick')['channels'] == 1
        assert 'my_kick' in sample_names()
        assert sample_names(group='mine') == ['my_kick']
        assert 'mine' in sample_groups()
        assert registered_samples() == ['my_kick']
        assert len(sample_bytes_b64('my_kick')) > 0

    def test_register_path(self, tmp_path):
        p = tmp_path / 'snap.wav'
        p.write_bytes(make_wav(channels=2))
        register_sample('snap', p)
        assert sample_info('snap')['channels'] == 2

    def test_identical_reregistration_is_noop(self):
        data = make_wav()
        register_sample('x', data)
        register_sample('x', data)
        assert registered_samples() == ['x']

    def test_different_bytes_require_replace(self):
        register_sample('x', make_wav(seed=1))
        with pytest.raises(ValueError, match='replace=True'):
            register_sample('x', make_wav(seed=2))
        register_sample('x', make_wav(channels=2, seed=2), replace=True)
        assert sample_info('x')['channels'] == 2

    def test_bundled_names_protected(self):
        with pytest.raises(ValueError, match='bundled'):
            register_sample('bb_kick', make_wav())
        # bundled lookups unchanged
        assert sample_info('bb_kick')['group'] == 'beatbox'

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            register_sample('nope', tmp_path / 'missing.wav')

    def test_bad_audio_reports_name(self):
        with pytest.raises(ValueError, match='bad_one'):
            register_sample('bad_one', b'FORM' + b'\x00' * 4 + b'AIFF' + b'\x00' * 32)

    def test_unregister(self):
        register_sample('gone', make_wav())
        unregister_sample('gone')
        assert registered_samples() == []
        with pytest.raises(KeyError):
            sample_info('gone')

    def test_unknown_sample_error_mentions_registry(self):
        with pytest.raises(KeyError, match='register_sample'):
            sample_info('definitely_not_a_sample')


class TestEngineIntegration:
    def test_registered_sample_flows_through_engine(self):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        register_sample('my_kick', make_wav(channels=1))
        eng = SuperSonicEngine([{
            'id': 'e0', 'type': 'new', 'defName': 'kl_sampler1',
            'start': 0.0, 'dur': 0.5,
            'pfields': {'buf': 'my_kick', 'amp': 0.5},
        }])
        assert 'my_kick' in eng.sample_assets
        assert eng.sample_assets['my_kick']['channels'] == 1

    def test_sampler_picks_def_by_channels(self):
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        register_sample('mono_s', make_wav(channels=1))
        register_sample('stereo_s', make_wav(channels=2))
        assert SynthDefInstrument.sampler('mono_s').defName == 'kl_sampler1'
        assert SynthDefInstrument.sampler('stereo_s').defName == 'kl_sampler2'

    def test_size_guardrail_warns(self):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        big = make_wav(channels=2, frames=2_000_000)  # ~8 MB
        register_sample('huge', big)
        with pytest.warns(UserWarning, match='embeds'):
            SuperSonicEngine([{
                'id': 'e0', 'type': 'new', 'defName': 'kl_sampler2',
                'start': 0.0, 'dur': 0.5,
                'pfields': {'buf': 'huge', 'amp': 0.5},
            }])


class TestSamplerPath:
    def test_path_auto_registers_with_prefix_stripped(self, tmp_path):
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        p = tmp_path / '3_perc_hit.wav'
        p.write_bytes(make_wav(channels=2))
        inst = SynthDefInstrument.sampler(p)
        assert inst.pfields['buf'] == 'perc_hit'
        assert inst.defName == 'kl_sampler2'
        assert 'perc_hit' in registered_samples()

    def test_bundled_name_never_shadowed(self):
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        inst = SynthDefInstrument.sampler('bb_kick')
        assert inst.pfields['buf'] == 'bb_kick'

    def test_missing_path_errors(self, tmp_path):
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        with pytest.raises(FileNotFoundError):
            SynthDefInstrument.sampler(tmp_path / 'missing.wav')


class TestFetchSamples:
    def _zip_with_kit(self, tmp_path):
        zpath = tmp_path / 'course.zip'
        with zipfile.ZipFile(zpath, 'w') as zf:
            zf.writestr('my_kit/kick.wav', make_wav(seed=1))
            zf.writestr('my_kit/snare/0_snare_a.wav', make_wav(seed=2))
        return zpath

    def test_fetch_and_unpack_local_zip(self, tmp_path):
        from klotho import fetch_samples
        zpath = self._zip_with_kit(tmp_path)
        dest = tmp_path / 'samples'
        out = fetch_samples(zpath.as_uri(), dest=dest)
        assert (out / 'my_kit' / 'kick.wav').is_file()
        assert (out / 'my_kit' / 'snare' / '0_snare_a.wav').is_file()

    def test_fetch_is_idempotent(self, tmp_path, capsys):
        from klotho import fetch_samples
        zpath = self._zip_with_kit(tmp_path)
        dest = tmp_path / 'samples'
        fetch_samples(zpath.as_uri(), dest=dest)
        marker = dest / 'my_kit' / 'sentinel'
        marker.write_text('keep me')
        fetch_samples(zpath.as_uri(), dest=dest)
        assert marker.read_text() == 'keep me'
        assert 'skipping download' in capsys.readouterr().out

    def test_upload_samples_errors_off_colab(self):
        from klotho import upload_samples
        with pytest.raises(RuntimeError, match='Colab'):
            upload_samples()
