#!/usr/bin/env python3
"""Generate a version-pinned Compose asset from the official template."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
DOCKERHUB_LATEST = "docker.io/eliyork/fntv-admin:latest"
GHCR_LATEST = "ghcr.io/eliyork/fntv-admin:latest"


def generate_release_compose(source: Path, destination: Path, version: str) -> None:
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("version must match vMAJOR.MINOR.PATCH")

    content = source.read_text(encoding="utf-8")
    dockerhub_count = content.count(DOCKERHUB_LATEST)
    ghcr_count = content.count(GHCR_LATEST)
    if dockerhub_count != 1:
        raise ValueError(
            f"expected exactly one Docker Hub latest image, found {dockerhub_count}"
        )
    if ghcr_count != 1:
        raise ValueError(f"expected exactly one GHCR latest image, found {ghcr_count}")

    generated = content.replace(DOCKERHUB_LATEST, f"docker.io/eliyork/fntv-admin:{version}")
    generated = generated.replace(GHCR_LATEST, f"ghcr.io/eliyork/fntv-admin:{version}")

    if DOCKERHUB_LATEST in generated or GHCR_LATEST in generated:
        raise ValueError("generated Compose still references a latest release image")
    if generated.count(f"docker.io/eliyork/fntv-admin:{version}") != 1:
        raise ValueError("generated Compose is missing the versioned Docker Hub image")
    if generated.count(f"ghcr.io/eliyork/fntv-admin:{version}") != 1:
        raise ValueError("generated Compose is missing the versioned GHCR fallback image")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generated, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    generate_release_compose(args.source, args.output, args.version)


if __name__ == "__main__":
    main()
