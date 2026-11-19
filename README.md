# breeze_tts

Local text-to-speech with Breeze-TTS-2 (`models/breeze-tts-2-q8_0.gguf`), served by `breeze-server` on
`127.0.0.1:8090`. This folder is used on its own from the command line, and by the video pipeline in
`/root/code/orchestration` (see [Used by the video pipeline](#used-by-the-video-pipeline)).

## Quick start
```bash
cd /root/code/breeze_tts
source venv/bin/activate

python mod.py --text "Hello there." --out hello.mp3
python mod.py --voice british_storyteller --file story.txt --out story.mp3
```
`mod.py` starts the model if it isn't already running, waits until it's up, then waits for the audio to finish
generating, writes the file and stops the model again. If a server was already running, for example the webui,
it is used and left running.

## Command line (`mod.py`)
| Flag | Meaning |
|---|---|
| `--text "..."` | the words to speak (default `Hello there.`) |
| `--file story.txt` | speak the contents of a text file instead |
| `--voice <name>` | a voice: a name in `voices/` (uses `<name>.txt` and/or `<name>.breeze`), or a path to a `.txt` / `.breeze` |
| `--instruction "..."` | describe the voice directly; overrides the voice file's description |
| `--cfg 3` | how closely to follow the description; overrides the voice file |
| `--seed 42` | which voice you get among all that fit the description; overrides the voice file |
| `--out out.wav` | output file. `.mp3` gives an mp3, `.wav` a 24 kHz mono wav |
| `--mode webui` | start the server with its web UI and keep it running (Ctrl+C stops it) |
| `--keep` | leave the model running after speaking |

For each setting, a command-line flag wins over the voice file, and the voice file wins over the default
(instruction: a warm male storyteller, cfg 3, seed 42). The cfg and seed actually used are printed before generating.

`./run.sh model` / `./run.sh webui` only starts the server, in the foreground. Its log from `mod.py` goes to `tts.log`.

## Voice files (`voices/<name>.txt`)
One file per narrator. The description is the text, and settings are optional lines anywhere in the file:
```
A middle-aged British man with a deep, warm, velvety voice ...
cfg: 3.5
seed: 42
sample: The harbour lights came on one by one.
# lines starting with # are comments
```
| Line | Meaning |
|---|---|
| any other text | the voice description sent to the model as `instruction` (lines are joined) |
| `cfg: 3.5` | cfg scale. Separators `:`, `=`, `-` or a space all work (`cfg-3.5` is fine) |
| `seed: 42` | seed: same description + seed = same voice; change it for a different person |
| `sample: ...` | only for the video pipeline: the sentence the voice is auditioned with |

## Cloned voices (`voices/<name>.breeze`)
A `.breeze` file is a cloned voice saved by `breeze-server` / `breeze-cli` (format: `Breeze-TTS-2.cpp/docs/voices.md`).
The server loads every `voices/*.breeze` at startup, and `--voice <name>` sends it as `voice_id`, so the clip is
not re-encoded. If `<name>.txt` exists too, its description steers the clone's delivery and its cfg/seed apply;
with only the `.breeze`, no description is sent (the default storyteller one is for designed voices only).
`--voice v1` uses both files, `--voice voices/v1.breeze` or `--voice v1.txt` just that one.
After adding a `.breeze`, restart the server; `mod.py` stops with a clear message if the server doesn't know it.

The reader is `read_voice()` in `file.py` (`voice_id`, `ref_text`, `description`, `seconds` come from the `.breeze`). A setting the file leaves out comes back as `None` and the caller
applies its default.

## From Python
```python
from file import read_voice, readfile
from tts import tts                      # needs the server already running

v = read_voice("british_storyteller")    # Voice(instruction=..., cfg=3.5, seed=None, sample=None)
tts(readfile("story.txt"), "story.mp3", instruction=v.instruction,
    cfg=v.cfg or 3, seed=v.seed if v.seed is not None else 42, voice_id=v.voice_id)
```
`tts()` blocks until generation has finished, then encodes by the output extension (needs `ffmpeg`).
`mod.py` runs at import time, so import `file` and `tts`, not `mod`.

## Used by the video pipeline
`/root/code/orchestration/tools/voice_build.py` (the voice stage of the narrated shorts):
- reads voice files through this folder's `file.read_voice`, so the format above is the only format
- starts and stops `breeze-server` itself, and waits for every sentence to finish
- writes `projects/<slug>/voice/voice.mp3` (the narration as an mp3) and `voice.wav` (48 kHz, used by the mix that
  goes into the mp4)

In a brief, `Voice file: british_storyteller` picks a file. `default.txt` is used when a brief names none. After
changing anything here, run `bash /root/code/orchestration/tools/selftest_voice.sh` (prints `SELFTEST OK`).

## Files
| Path | Purpose |
|---|---|
| `mod.py` | command line: start model, speak, stop model |
| `tts.py` | `tts()`: one request to the server, saved as wav/mp3 |
| `file.py` | `readfile()`, `read_voice()`, `list_voices()`, `read_breeze()` |
| `voices/` | your hand-picked voice files |
| `run.sh` | starts `breeze-server` (`model` or `webui`) |
| `Breeze-TTS-2.cpp/` | the engine; its own docs are in `Breeze-TTS-2.cpp/docs/` |
