# breeze_tts

Local text-to-speech with Breeze-TTS-2, served by `breeze-server` on `127.0.0.1:8090`.

## About

Runs a [Breeze-TTS-2 GGUF](https://huggingface.co/HoppouAI/Breeze-TTS-2.cpp) model locally, quantized to 8-bit so it fits in a 3060 Ti's limited VRAM. You give it a script and a voice, and it writes an audio file. It's mostly called by the [orchestration skill](https://github.com/JaydenYip3/Video-Orchestration/blob/main/.claude/skills/narrated-short/SKILL.md).

## Sample:
[airbnb-obama-os.wav](https://github.com/user-attachments/files/35069887/airbnb-obama-os.wav)


## Usage

```bash
source venv/bin/activate

python mod.py --text "Hello there." --out hello.mp3
python mod.py --voice british_storyteller --file story.txt --out story.mp3
```

`mod.py` starts the model, generates the audio and then stops the model. If a server is already running (for example the web UI), `mod.py` uses it and leaves it running.

| Flag | Meaning |
|---|---|
| `--text` / `--file` | words to speak, or a text file |
| `--voice <name>` | a voice from `voices/` |
| `--instruction "..."` | describe the voice directly |
| `--cfg`, `--seed` | override the voice file's settings |
| `--out` | `.mp3` or `.wav` |
| `--mode webui` | run the web UI |
| `--keep` | leave the model running |

## Voices

Each narrator is a text file in `voices/<name>.txt`:

```
A middle-aged British man with a deep, warm, velvety voice.
cfg: 3.5
seed: 42
```

- The text is the voice description.
- The same description and seed always give the same voice. Change `seed` to get a different voice that fits the same description.
- `cfg` sets how closely the model follows the description.

A cloned voice is saved as `voices/<name>.breeze`. If a `.txt` with the same name exists, its description and settings steer the clone. Restart the server after adding a `.breeze` file.

## From Python

```python
from file import read_voice, readfile
from tts import tts  # needs the server running

v = read_voice("british_storyteller")
tts(readfile("story.txt"), "story.mp3", instruction=v.instruction,
    cfg=v.cfg or 3, seed=v.seed or 42, voice_id=v.voice_id)
```
