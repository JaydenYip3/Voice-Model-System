#!/bin/bash
set -e
cd "$(dirname "$0")"

MODEL=./models/breeze-tts-2-q8_0.gguf

case "$1" in
  webui)
    ./Breeze-TTS-2.cpp/build/breeze-server "$MODEL" --host 0.0.0.0 --port 8090 --webui
    ;;
  model)
    ./Breeze-TTS-2.cpp/build/breeze-server "$MODEL" --host 0.0.0.0 --port 8090
    ;;
  *)
    echo "usage: ./run.sh {webui|model}"
    ;;
esac
