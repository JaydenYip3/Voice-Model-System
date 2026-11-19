import argparse, subprocess, socket, time, os, signal
from file import readfile, read_voice
from tts import tts, has_voice

os.chdir(os.path.dirname(os.path.abspath(__file__)))

parser = argparse.ArgumentParser(description="Run Breeze TTS")

# DEFAULT: without flags it just runs the model

#To run the model
parser.add_argument("--file", help="text-file to speech")
parser.add_argument("--text", default="Hello there.",
                    help="text to speak")
parser.add_argument("--mode", choices=["model", "webui"], default="model",
                    help="web or just model")
parser.add_argument("--out", default="out.wav",
                    help="output file; .wav or .mp3 (format follows the extension)")
parser.add_argument("--voice",
                    help="voice: a name in voices/ (uses <name>.txt and/or <name>.breeze) "
                         "or a path to a .txt or .breeze file")
parser.add_argument("--instruction",
                    help="voice description for the model (overrides --voice)")
parser.add_argument("--seed", type=int,
                    help="random seed (overrides the voice file, default 42)")
parser.add_argument("--cfg", type=float,
                    help="cfg scale, how closely to follow the instruction "
                         "(overrides the voice file, default 3)")
parser.add_argument("--keep", action="store_true",
                    help="keep the model running after speaking")

args = parser.parse_args()

DEFAULT_INSTRUCTION = "A deep, warm male storyteller, slow and calm."
DEFAULT_CFG = 3
DEFAULT_SEED = 42

# precedence: CLI flag > voice file > default
voice = read_voice(args.voice) if args.voice else None
voice_id = voice and voice.voice_id
# a cloned voice (.breeze) brings its own sound, so the default description is
# only used for designed voices; with a clone, no instruction = server default
instruction = (args.instruction or (voice and voice.instruction)
               or (None if voice_id else DEFAULT_INSTRUCTION))
cfg = next(v for v in (args.cfg, voice and voice.cfg, DEFAULT_CFG) if v is not None)
seed = next(v for v in (args.seed, voice and voice.seed, DEFAULT_SEED) if v is not None)

def is_up():
    try:
        socket.create_connection(("127.0.0.1", 8090), timeout=1).close()
        return True
    except OSError:
        return False

def start_model(mode):
    log = open("tts.log", "w")
    # own process group, so stopping it also kills breeze-server (run.sh's child)
    proc = subprocess.Popen(["./run.sh", mode], stdout=log, stderr=log,
                            start_new_session=True)
    for _ in range(60):
        if is_up():
            print("model is up")
            return proc
        if proc.poll() is not None:
            break
        time.sleep(1)
    stop_model(proc)
    raise RuntimeError("model didn't start, check tts.log")

def stop_model(proc):
    if proc is None:              # server was already running before us: leave it
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    proc.wait()

if is_up():
    print("model already running, using it")
    proc = None
else:
    proc = start_model(args.mode)

try:
    if voice_id and not has_voice(voice_id):
        raise SystemExit(f"server has no voice '{voice_id}'. It loads voices/*.breeze at startup: "
                         "put the file in voices/ and restart the server.")

    if args.mode == "model" and (args.file or args.text):
        text = readfile(args.file) if args.file else args.text
        print(f"cfg={cfg} seed={seed}" + (f" voice_id={voice_id}" if voice_id else ""))
        tts(text, args.out, instruction=instruction, cfg=cfg, seed=seed, voice_id=voice_id)
        print(f"wrote {args.out}")

    if args.mode == "webui" or args.keep:
        print("model running, press Ctrl+C to stop")
        try:
            if proc:
                proc.wait()
        except KeyboardInterrupt:
            pass
finally:
    stop_model(proc)
