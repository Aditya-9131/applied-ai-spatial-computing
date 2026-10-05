"""Weight fetcher for all ML models used by the pipeline.

Models and licenses:
  - Depth Anything V2 Metric (Small): Liangbo Xie et al., 2024
    Weights: https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf
    License: Apache 2.0
    Dataset trained on: HyperSim + Virtual KITTI (indoor metric variant)
    Task: monocular metric depth estimation for indoor scenes

Usage:
  python scripts/fetch_weights.py
  python scripts/fetch_weights.py --models depth_anything  (default)
  python scripts/fetch_weights.py --list

Weights are cached to WEIGHTS_DIR (default: weights/).
The pipeline checks for cached weights at startup and skips network calls
on subsequent runs.  Pass --force to re-download.
"""

import os
import sys
import argparse

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS_DIR = os.path.join(BASE_DIR, "weights")

MODELS = {
    "depth_anything_v2_metric_small": {
        "hf_repo":  "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf",
        "local_dir": os.path.join(WEIGHTS_DIR, "depth_anything_v2_metric_small"),
        "description": "Depth Anything V2 Metric Indoor Small (~100 MB, Apache 2.0)",
        "license": "Apache-2.0",
        "citation": "Liangbo Xie et al., 2024. Depth Anything V2.",
    },
}

def fetch_model(name: str, force: bool = False) -> str:
    """Download a model from HuggingFace Hub and return local path."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    spec = MODELS[name]
    local_dir = spec["local_dir"]

    if os.path.isdir(local_dir) and not force:
        config_path = os.path.join(local_dir, "config.json")
        if os.path.exists(config_path):
            print(f"[CACHED] {name} → {local_dir}")
            return local_dir

    print(f"[DOWNLOADING] {name}")
    print(f"  Repo:    {spec['hf_repo']}")
    print(f"  License: {spec['license']}")
    print(f"  {spec['citation']}")
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(
        repo_id=spec["hf_repo"],
        local_dir=local_dir,
        ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
    )
    print(f"[DONE] {name} → {local_dir}")
    return local_dir


def list_models():
    print("Available models:")
    for name, spec in MODELS.items():
        local = spec["local_dir"]
        cached = "✓ cached" if os.path.isdir(local) and os.path.exists(os.path.join(local, "config.json")) else "  not downloaded"
        print(f"  {name:45s}  {cached}")
        print(f"    {spec['description']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch ML model weights for the spatial pipeline.")
    parser.add_argument("--models", nargs="+", default=["depth_anything_v2_metric_small"],
                        choices=list(MODELS.keys()), help="Which models to download")
    parser.add_argument("--list", action="store_true", help="List available models and cache status")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    if args.list:
        list_models()
    else:
        os.makedirs(WEIGHTS_DIR, exist_ok=True)
        for m in args.models:
            fetch_model(m, force=args.force)
        print("\nAll requested weights ready.")
