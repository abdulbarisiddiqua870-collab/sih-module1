from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np
from tests.conftest import render_label


def save(image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), bgr)
    print(f"wrote {path}")


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "test_images"
    save(render_label(), out_dir / "sample_label.png")
    save(
        render_label(background=(40, 40, 45), foreground=(230, 230, 230)),
        out_dir / "sample_label_dark.png",
    )
    blurred = cv2.GaussianBlur(
        cv2.cvtColor(np.array(render_label()), cv2.COLOR_RGB2BGR), (0, 0), sigmaX=6
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_dir / "sample_label_blurry.png"), blurred)
    print(f"wrote {out_dir / 'sample_label_blurry.png'}")


if __name__ == "__main__":
    main()
