"""Standalone corpus cost estimator."""
from .run_experiment import main

if __name__ == "__main__":
    raise SystemExit(main(["--estimate-only"]))
