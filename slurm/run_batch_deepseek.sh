#!/bin/bash
#SBATCH --job-name=vllm_offline_mn
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1          # one Ray process per node
#SBATCH --gres=gpu:4                 # 4× A100 80GB per node
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G                   # per node
#SBATCH --time=04:00:00
#SBATCH --constraint=gpu40
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=your-email@domain.edu

# ====== Env & modules ======
module load anaconda3/2025.6
eval "$(conda shell.bash hook)"
conda activate godsreach2

# OFFLINE: never hit the internet
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1
export RAY_USAGE_STATS_ENABLED=0
export TOKENIZERS_PARALLELISM=true

# Caches on scratch (adjust to your paths)
export HF_HOME=/scratch/gpfs/JORDANAT/mg9965/God-s-Reach/models
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME
export VLLM_CACHE_DIR=/scratch/gpfs/JORDANAT/mg9965/vLLM-cache
export TRITON_CACHE_DIR=$VLLM_CACHE_DIR/triton
export XDG_CACHE_HOME=$VLLM_CACHE_DIR/xdg
mkdir -p "$VLLM_CACHE_DIR" "$TRITON_CACHE_DIR" "$XDG_CACHE_HOME"

# Perf hints
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export NCCL_DEBUG=WARN
export NCCL_P2P_LEVEL=NVL
# If your cluster uses Infiniband, uncomment the correct interface:
# export NCCL_SOCKET_IFNAME=ib0

# Your local model path (no internet required)
export DEEPSEEK_MODEL_PATH=/scratch/gpfs/JORDANAT/mg9965/models/deepseek-ai--DeepSeek-V2.5

# ====== Host discovery ======
HEAD_HOST=$(scontrol show hostnames "$SLURM_NODELIST" | head -n 1)
HEAD_IP=$(getent hosts "$HEAD_HOST" | awk '{print $1}')
RAY_PORT=6379
VLLM_PORT=8000
TP_SIZE=8                    # 2 nodes × 4 GPUs

echo "Head host: $HEAD_HOST ($HEAD_IP)"
echo "Nodes: $SLURM_JOB_NUM_NODES  GPUs/node: 4  TP: $TP_SIZE"

cd /scratch/gpfs/JORDANAT/mg9965/God-s-Reach/designspace_extractor

# ====== Start Ray on all nodes ======
# Use srun so each node runs its branch of this if/else
srun --ntasks=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 bash -lc '
  if [ "$SLURM_NODEID" -eq 0 ]; then
    ray start --head --node-ip-address="'"$HEAD_IP"'" --port='"$RAY_PORT"' --num-gpus=4 --disable-usage-stats
  else
    ray start --address="'"$HEAD_IP:$RAY_PORT"'" --num-gpus=4 --disable-usage-stats
  fi
'

# ====== Start vLLM API server on the head node only ======
srun --nodes=1 --ntasks=1 -w "$HEAD_HOST" bash -lc "
  python -m vllm.entrypoints.api_server \
    --model \"$DEEPSEEK_MODEL_PATH\" \
    --tensor-parallel-size $TP_SIZE \
    --distributed-executor-backend ray \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.92 \
    --max-model-len 4096 \
    --host 0.0.0.0 \
    --port $VLLM_PORT \
    --download-dir \"$HF_HOME\" \
    --disable-log-stats \
    > logs/vllm_server_${SLURM_JOB_ID}.log 2>&1 &
"

# ====== Wait for the API to be healthy (head node) ======
srun --nodes=1 --ntasks=1 -w "$HEAD_HOST" bash -lc "
  echo 'Waiting for vLLM API on $HEAD_IP:$VLLM_PORT...'
  for i in {1..120}; do
    python - <<'PY'
import socket,sys,os
host=os.environ.get('HEAD_IP','127.0.0.1')
port=int(os.environ.get('VLLM_PORT','8000'))
s=socket.socket(); s.settimeout(1.0)
try:
    s.connect((host,port)); print('UP'); sys.exit(0)
except Exception: sys.exit(1)
PY
    if [ \$? -eq 0 ]; then break; fi
    sleep 2
  done
"

# ====== Run your batch client on the head node, pointing to the local API ======
srun --nodes=1 --ntasks=1 -w "$HEAD_HOST" bash -lc "
  export LLM_ENDPOINT=http://$HEAD_IP:$VLLM_PORT
  echo Using LLM endpoint: \$LLM_ENDPOINT
  python run_batch_extraction.py \
    --papers '../papers' \
    --output 'batch_processing_results_deepseek.json' \
    --llm-endpoint \$LLM_ENDPOINT
"

# ====== Clean shutdown ======
srun --ntasks=$SLURM_JOB_NUM_NODES --ntasks-per-node=1 bash -lc 'ray stop'
echo '✅ Done.'
