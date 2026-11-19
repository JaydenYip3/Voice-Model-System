"""Reading text files and voice files. See README.md for the voice file format.

This module is also imported by /root/code/orchestration/tools/voice_build.py,
so it must stay importable without side effects.
"""
import os
import re
import struct
from dataclasses import dataclass, field
from typing import Optional

VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")

# numeric settings lines in a voice file, e.g. "cfg: 3.5", "seed=7", "cfg-3.5"
_PARAM_RE = re.compile(r"^\s*(cfg|seed)\s*[:=\-]?\s*(-?\d+(?:\.\d+)?)\s*$", re.IGNORECASE)
_PARAM_TYPES = {"cfg": float, "seed": int}
# "sample: <sentence>", the line the voice is auditioned with
_SAMPLE_RE = re.compile(r"^\s*sample\s*:\s*(\S.*?)\s*$", re.IGNORECASE)
# saved-voice ids the server accepts (they are the .breeze file's name)
_VOICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_VOICE_EXTS = (".txt", ".breeze")
FRAMES_PER_SECOND = 12.5


@dataclass
class Voice:
    instruction: str = ""          # "" when only a .breeze file exists
    cfg: Optional[float] = None
    seed: Optional[int] = None
    sample: Optional[str] = None
    # from <name>.breeze, a cloned voice saved by breeze-server / breeze-cli
    voice_id: Optional[str] = None
    ref_text: Optional[str] = None
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    seconds: Optional[float] = None


def readfile(path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def list_voices():
    """Names of the voice files in voices/ (.txt and/or .breeze)."""
    if not os.path.isdir(VOICES_DIR):
        return []
    return sorted({os.path.splitext(f)[0] for f in os.listdir(VOICES_DIR)
                   if f.endswith(_VOICE_EXTS)})


def voice_files(name_or_path):
    """Find a voice's files. Returns (txt_path, breeze_path), either may be None.

    A path ending in .txt or .breeze uses just that file. A bare name (or a path
    without extension) picks up both <name>.txt and <name>.breeze if they exist,
    looking next to the given path first and then in voices/.
    """
    name_or_path = str(name_or_path)
    if name_or_path.endswith(_VOICE_EXTS):
        if not os.path.isfile(name_or_path):
            alt = os.path.join(VOICES_DIR, os.path.basename(name_or_path))
            if not os.path.isfile(alt):
                raise FileNotFoundError(f"voice file not found: {name_or_path}")
            name_or_path = alt
        if name_or_path.endswith(".breeze"):
            return None, name_or_path
        return name_or_path, None

    for base in (name_or_path, os.path.join(VOICES_DIR, os.path.basename(name_or_path))):
        found = [base + e if os.path.isfile(base + e) else None for e in _VOICE_EXTS]
        if any(found):
            return tuple(found)
    have = ", ".join(list_voices()) or "none"
    raise FileNotFoundError(f"voice not found: {name_or_path} (voices available: {have})")


def voice_path(name_or_path) -> str:
    """Path of a voice's .txt file (kept for older callers; see voice_files)."""
    txt, _ = voice_files(name_or_path)
    if txt is None:
        raise FileNotFoundError(f"voice {name_or_path} has no .txt file")
    return txt


def read_breeze(path) -> dict:
    """Read the header of a .breeze file (see Breeze-TTS-2.cpp/docs/voices.md).

    Returns voice_id, ref_text, description, metadata and seconds. The codes
    themselves are not read: the server loads them from voices/ at startup.
    """
    with open(path, "rb") as f:
        data = f.read()

    def u32(off):
        if off + 4 > len(data):
            raise ValueError(f"{path}: truncated .breeze file")
        return struct.unpack_from("<I", data, off)[0], off + 4

    def string(off):
        n, off = u32(off)
        if off + n > len(data):
            raise ValueError(f"{path}: truncated .breeze file")
        return data[off:off + n].decode("utf-8"), off + n

    if data[:4] != b"BRZV":
        raise ValueError(f"{path}: not a .breeze voice file")
    version, _ = u32(4)
    if version not in (1, 2):
        raise ValueError(f"{path}: unsupported .breeze version {version}")
    n_codebooks, _ = u32(12)
    frames, _ = u32(16)
    ref_text, off = string(20)
    description, metadata = None, {}
    if version == 2:
        description, off = string(off)
        n_fields, off = u32(off)
        for _ in range(n_fields):
            k, off = string(off)
            v, off = string(off)
            metadata[k] = v
    if len(data) - off != frames * n_codebooks * 4:
        raise ValueError(f"{path}: .breeze file size doesn't match its header")

    voice_id = os.path.splitext(os.path.basename(path))[0]
    if not _VOICE_ID_RE.match(voice_id):
        raise ValueError(f"{path}: voice name must be letters, digits, - or _ (max 64)")
    return dict(voice_id=voice_id, ref_text=ref_text, description=description or None,
                metadata=metadata, seconds=round(frames / FRAMES_PER_SECOND, 2))


def read_voice(name_or_path) -> Voice:
    """Read a voice: <name>.txt (instruction + settings) and/or <name>.breeze
    (a saved cloned voice).

    In the .txt, lines like "cfg: 3.5" or "seed: 42" (":", "=", "-" or a space
    as separator) and "sample: <sentence>" are settings; lines starting with #
    are comments; everything else is the instruction. Settings left out are
    None, so the caller can apply its own defaults.

    With a .breeze, voice_id is set and the server clones that voice; the
    .txt's instruction (if any) then steers its delivery.
    """
    txt, breeze = voice_files(name_or_path)
    params = {}
    if breeze:
        params.update(read_breeze(breeze))
    if txt:
        params.update(_read_txt(txt, require_instruction=breeze is None))
    return Voice(**params)


def _read_txt(path, require_instruction=True) -> dict:
    params = {}
    lines = []
    for line in readfile(path).splitlines():
        if line.strip().startswith("#"):
            continue
        m = _PARAM_RE.match(line)
        s = _SAMPLE_RE.match(line)
        if m:
            key = m.group(1).lower()
            try:
                params[key] = _PARAM_TYPES[key](m.group(2))
            except ValueError:
                raise ValueError(f"{path}: bad value for {key}: {m.group(2)!r}")
        elif s:
            params["sample"] = s.group(1)
        elif line.strip():
            lines.append(line.strip())

    if not lines and require_instruction:
        raise ValueError(f"{path}: voice file has no instruction text")
    params["instruction"] = " ".join(lines)
    return params
