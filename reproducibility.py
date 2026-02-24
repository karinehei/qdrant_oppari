# -*- coding: utf-8 -*-
"""
Reproducibility Module

Provides seed setting, environment info collection, and git metadata
for research reproducibility. Safe fallbacks when dependencies are missing.
"""

from __future__ import annotations

import logging
import os
import platform
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def set_global_seed(seed: int) -> None:
    """
    Set global random seeds for reproducibility.
    Does not raise if numpy/torch are not installed.
    """
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        logger.debug("numpy not installed, skipping numpy seed")
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        logger.debug("torch not installed, skipping torch seed")


def collect_environment_info() -> dict[str, Any]:
    """Collect environment info for reproducibility metadata."""
    info: dict[str, Any] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "executable": sys.executable,
        "current_working_directory": str(Path.cwd()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        info["hostname"] = platform.node()
    except Exception:
        info["hostname"] = None

    try:
        info["cpu_info"] = platform.processor() or platform.machine()
    except Exception:
        info["cpu_info"] = None

    package_versions: dict[str, str | None] = {}
    for pkg in ("qdrant_client", "sentence_transformers", "transformers", "torch", "numpy"):
        try:
            mod = __import__(pkg)
            package_versions[pkg] = getattr(mod, "__version__", None)
        except ImportError:
            package_versions[pkg] = None
        except Exception:
            package_versions[pkg] = None
    info["package_versions"] = package_versions

    info["gpu_info"] = None
    try:
        import torch

        if torch.cuda.is_available():
            info["gpu_info"] = {
                "device_count": torch.cuda.device_count(),
                "device_name": torch.cuda.get_device_name(0) if torch.cuda.device_count() else None,
            }
    except ImportError:
        pass
    except Exception:
        pass

    return info


def get_git_commit_hash() -> str | None:
    """Return git HEAD commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug("Could not get git commit: %s", e)
    return None


def get_git_branch() -> str | None:
    """Return current git branch, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.debug("Could not get git branch: %s", e)
    return None


def build_reproducibility_metadata(seed: int | None = None) -> dict[str, Any]:
    """Build combined reproducibility metadata dict."""
    meta: dict[str, Any] = {
        "environment_info": collect_environment_info(),
        "git_commit_hash": get_git_commit_hash(),
        "git_branch": get_git_branch(),
    }
    if seed is not None:
        meta["seed"] = seed
    return meta
