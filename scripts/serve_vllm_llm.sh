#!/usr/bin/env bash
# HemaGuide LLM inference via vLLM (OpenAI-compatible /v1/chat/completions).
# Default GPU: card 3 (mostly free). Override with CUDA_DEVICE / PORT / MODEL_PATH.
#
# First-time setup (needs HuggingFace access):
#   huggingface-cli download openai/gpt-oss-20b --local-dir /data/wilson_2/de/models/openai/gpt-oss-20b
#   MODEL_PATH=/data/wilson_2/de/models/openai/gpt-oss-20b bash scripts/serve_vllm_llm.sh
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-openai/gpt-oss-20b}"
SERVED_NAME="${SERVED_NAME:-gpt-oss-20b}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8010}"
CUDA_DEVICE="${CUDA_DEVICE:-3}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
VLLM_BIN="${VLLM_BIN:-/opt/ac2/bin/vllm}"

export CUDA_VISIBLE_DEVICES="$CUDA_DEVICE"

echo "Starting vLLM LLM: model=$MODEL_PATH served=$SERVED_NAME gpu=$CUDA_DEVICE port=$PORT"

exec "$VLLM_BIN" serve "$MODEL_PATH" \
  --served-model-name "$SERVED_NAME" \
  --host "$HOST" \
  --port "$PORT" \
  --gpu-memory-utilization "$GPU_MEM_UTIL" \
  --max-model-len "$MAX_MODEL_LEN"
