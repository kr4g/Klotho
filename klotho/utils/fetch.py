"""Helpers for getting sample files onto the notebook runtime.

Colab runtimes are wiped between sessions, so course notebooks download
instructor-hosted audio at the top of the notebook instead of asking
students to re-upload it. :func:`fetch_samples` covers hosted archives
(plain HTTPS, GitHub raw/release URLs, Hugging Face ``resolve`` URLs,
and Google Drive share links via the optional ``gdown`` package);
:func:`upload_samples` wraps Colab's file-upload picker. Both work in
local Jupyter too — the same setup cell runs unchanged in either
environment, and ``SynthDefKit.from_folder`` / ``sampler`` then point at
the resulting local files.
"""

import shutil
import zipfile
import tarfile
from pathlib import Path
from urllib.request import urlopen, Request

_ARCHIVE_SUFFIXES = ('.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2')


def _is_google_drive_url(url):
    return 'drive.google.com' in url or 'docs.google.com' in url


def _looks_like_archive(path):
    name = str(path).lower()
    return any(name.endswith(sfx) for sfx in _ARCHIVE_SUFFIXES)


def _download_http(url, target):
    """Stream *url* to *target* via a ``.part`` temp so an interrupted
    download is never mistaken for a complete file."""
    part = target.with_suffix(target.suffix + '.part')
    req = Request(url, headers={'User-Agent': 'klotho-fetch'})
    with urlopen(req, timeout=120) as resp, part.open('wb') as out:
        shutil.copyfileobj(resp, out)
    part.replace(target)
    return target


def fetch_samples(url, dest='samples', *, unzip=True, overwrite=False):
    """Download (and unpack) hosted sample audio into *dest*.

    Idempotent by design: when *dest* already exists and is non-empty,
    the download is skipped (pass ``overwrite=True`` to refresh), so the
    setup cell can be re-run freely.

    Parameters
    ----------
    url : str
        A direct file URL (plain HTTPS, GitHub raw/release asset,
        Hugging Face ``.../resolve/...``), or a Google Drive share link
        (requires ``pip install gdown``).
    dest : str or Path, optional
        Directory to place the files in (default ``'samples'``, relative
        to the working directory — ``/content`` on Colab).
    unzip : bool, optional
        Unpack ``.zip``/``.tar*`` archives into *dest* (default True).
        The archive itself is kept next to *dest* so re-runs skip the
        download.
    overwrite : bool, optional
        Re-download and re-unpack even when *dest* is populated.

    Returns
    -------
    Path
        *dest*, ready for ``SynthDefKit.from_folder`` /
        ``SynthDefInstrument.sampler``.
    """
    dest = Path(dest)
    if dest.is_dir() and any(dest.iterdir()) and not overwrite:
        print(f"[klotho] {dest} already populated; skipping download "
              f"(overwrite=True to refresh)")
        return dest

    dest.mkdir(parents=True, exist_ok=True)

    filename = Path(url.split('?')[0].rstrip('/')).name or 'download'
    is_drive = _is_google_drive_url(url)
    target = dest.parent / filename if _looks_like_archive(filename) else dest / filename

    if is_drive:
        try:
            import gdown
        except ImportError:
            raise ImportError(
                "Google Drive links need the gdown package: "
                "%pip install gdown  — or host the file as a direct "
                "HTTPS URL (GitHub release, Hugging Face, ...) instead."
            ) from None
        # Drive URLs rarely expose a filename; let gdown name it, into
        # the parent so an archive doesn't end up inside dest.
        out = gdown.download(url=url, output=str(dest.parent) + '/',
                             quiet=False, fuzzy=True)
        if out is None:
            raise RuntimeError(
                f"gdown could not download {url!r}. Check that the link "
                f"is shared as 'Anyone with the link'."
            )
        target = Path(out)
    else:
        _download_http(url, target)

    if unzip and _looks_like_archive(target):
        if str(target).lower().endswith('.zip'):
            with zipfile.ZipFile(target) as zf:
                zf.extractall(dest)
        else:
            with tarfile.open(target) as tf:
                tf.extractall(dest, filter='data')
        print(f"[klotho] unpacked {target.name} -> {dest}")
    else:
        print(f"[klotho] downloaded {target}")
    return dest


def upload_samples(dest='samples'):
    """Colab-only: open the file-upload picker and save files into *dest*.

    In local Jupyter this raises with a pointer to just copying files
    into the folder — the rest of the workflow is identical.

    Returns
    -------
    Path
        *dest* containing the uploaded files.
    """
    try:
        from google.colab import files  # type: ignore
    except ImportError:
        raise RuntimeError(
            "upload_samples() only works on Google Colab. Locally, just "
            "copy your .wav files into the folder (e.g. 'samples/') and "
            "point SynthDefKit.from_folder / sampler at them."
        ) from None
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    uploaded = files.upload()
    for fname, data in uploaded.items():
        (dest / Path(fname).name).write_bytes(data)
    print(f"[klotho] saved {len(uploaded)} file(s) to {dest}")
    return dest
