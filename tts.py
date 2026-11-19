import requests, subprocess

BASE = "http://127.0.0.1:8090"
URL = BASE + "/v1/audio/speech"

def tts(text, out_path, instruction="A deep, warm male storyteller, slow and calm.",
        cfg=3, seed=42, voice_id=None):
    """Speak `text` and save it to `out_path`. The format follows the extension
    (.wav, .mp3, ...). Blocks until the server has finished generating.

    voice_id clones a saved voice (voices/<id>.breeze); instruction then steers
    its delivery. instruction=None or "" leaves it out (server default)."""
    data = {                          # form fields; the server reads these by name
        "text": text,
        "cfg_scale": cfg,
        "seed": seed,
    }
    if instruction:
        data["instruction"] = instruction
    if voice_id:
        data["voice_id"] = voice_id
    r = requests.post(URL, data=data, timeout=300)   # give up after 5 minutes
    if r.status_code == 404 and voice_id:
        raise RuntimeError(f"server doesn't know voice '{voice_id}'; it loads voices/*.breeze "
                           "at startup, so restart it after adding the file")
    r.raise_for_status()              # raise an error if the server returned 4xx/5xx

    # the server returns raw 24 kHz 16-bit mono PCM; ffmpeg encodes it by extension
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-"]
    if str(out_path).lower().endswith(".mp3"):
        cmd += ["-c:a", "libmp3lame", "-q:a", "2"]   # ~190 kbps VBR
    subprocess.run(cmd + [str(out_path)], input=r.content, check=True)


def has_voice(voice_id) -> bool:
    """True if the running server has loaded this saved/cached voice."""
    return requests.get(f"{BASE}/v1/voices/{voice_id}", timeout=10).status_code == 200
