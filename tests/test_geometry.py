
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "src")
)

from geometry import load_cad, load_scan


def test_load_nominal_cad():

    cad_path = (
        PROJECT_ROOT / "data/nominal/bracket.stl"
    )

    mesh = load_cad(cad_path)

    assert not mesh.is_empty()
    assert len(mesh.vertices) > 0
    assert len(mesh.triangles) > 0


def test_load_synthetic_scan():

    scan_path = (
        PROJECT_ROOT / "data/synthetic/raw_scan.ply"
    )

    cloud = load_scan(scan_path)

    assert not cloud.is_empty()
    assert len(cloud.points) > 1000
