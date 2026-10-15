# 3D Scan-to-CAD Dimensional Inspection System

**An automated 3D inspection prototype for point-cloud registration, dimensional measurement, geometric defect detection, and quality reporting.**

Built with Python, Open3D, NumPy, SciPy, and DBSCAN.

## Overview

Manufacturing inspection requires comparing the geometry of a produced component against its nominal CAD design. Real 3D scans introduce challenges such as measurement noise, incomplete surface coverage, uncertain alignment, and geometric defects.

This project implements a modular **scan-to-CAD inspection pipeline** that processes a 3D point cloud, aligns it with a nominal CAD mesh, extracts geometric features, evaluates demonstration tolerances, and generates structured inspection reports.

The system was developed using a synthetic L-bracket inspection experiment and evaluated further using real 3D scans from the Real3D-AD dataset.

### Key capabilities

- Global point-cloud registration using FPFH features and RANSAC
- ICP refinement with stable-region alignment
- Multi-start registration for improved robustness
- Feature-aware registration quality validation
- Hole diameter, center-position, and spacing measurements
- Flange deviation and angular measurements
- Angular coverage and circle-fitting quality checks
- DBSCAN-based geometric anomaly localization
- PASS / FAIL / REVIEW inspection decisions
- JSON reporting and colored point-cloud visualization
- Command-line execution and automated testing

## System Architecture

```text
Nominal CAD Mesh       Raw 3D Scan
       |                    |
       +---------+----------+
                 |
                 v
         Geometry Loading
                 |
                 v
       FPFH + RANSAC
                 |
                 v
       Stable-Region ICP
                 |
                 v
      Multi-Start Registration
                 |
                 v
     Registration Quality Gate
                 |
          +------+------+
          |             |
       ACCEPTABLE      REVIEW
          |             |
          v             v
   Feature Extraction   Stop Inspection
          |
          v
   Hole and Flange Measurements
          |
          v
   Coverage and Quality Checks
          |
          v
   Tolerance Evaluation
          |
          v
   DBSCAN Defect Localization
          |
          v
   JSON Report + Colored PLY
```

## 1. Synthetic L-Bracket Inspection

The initial experiment uses an L-bracket CAD model with two mounting holes.

A controlled deformation was introduced into the horizontal flange to simulate a manufacturing defect.

The synthetic scanning workflow includes:

1. Sampling the defective mesh into a point cloud.
2. Applying a rigid transformation to simulate an unknown scanner pose.
3. Adding Gaussian positional noise.
4. Removing points to simulate incomplete observations.
5. Introducing outliers.
6. Registering the resulting scan against the nominal CAD.
7. Performing dimensional inspection.

The original synthetic defect introduced a maximum vertex displacement of **3.0 mm**.

The nominal bracket bounding-box dimensions are approximately **15 × 49.5 × 49.5 mm**.

### Dimensional inspection

The system measures:

- Hole 1 and Hole 2 diameters
- Hole-center positions
- Hole-center spacing
- Horizontal-flange deviation from the nominal plane
- Angular deviation between nominal and measured flange planes

Demonstration tolerances are defined in `configs/inspection_config.json`.

The inspection engine returns:

| Status | Meaning |
|---|---|
| PASS | The measurement satisfies the configured tolerance rule |
| FAIL | The measurement violates the configured tolerance rule |
| REVIEW | Measurement evidence or registration quality is insufficient |

These are prototype inspection decisions, not certified industrial metrology results.

## 2. Registration Robustness

A key finding emerged during repeated registration experiments.

The original FPFH + RANSAC + ICP pipeline occasionally converged to an incorrect pose approximately **180°** away from the synthetic ground truth.

Despite this catastrophic error, ICP fitness remained approximately **98.7%**.

This demonstrated that high global correspondence fitness alone was insufficient to validate registration correctness.

### Feature-aware registration validation

An additional quality gate was introduced to check whether expected mounting-hole geometry remained observable after alignment.

Incorrect registrations that placed the expected features in inconsistent locations were flagged for review.

The gate also detects insufficient feature observations, although it cannot independently distinguish occlusion from every possible registration error.

### Multi-start registration

A multi-start strategy was implemented to generate several registration candidates, apply quality checks, and select an acceptable candidate using a provisional RMSE ranking rule.

**Observed benchmark results:**

| Metric | Single-start | Multi-start |
|---|---:|---:|
| Trials | 20 | 20 |
| Correct poses accepted | 16 | 20 |
| Incorrect poses accepted | 0 | 0 |
| REVIEW outcomes | 4 | 0 |
| Acceptance rate | 80% | 100% |
| Mean runtime | 2.791 s | 7.084 s |

Multi-start improved the observed acceptance rate by 20 percentage points, at approximately 2.54× the mean runtime.

These results were obtained from repeated stochastic trials on one synthetic scan and do not establish general production reliability.

## 3. Dimensional Measurement and Coverage

Hole geometry is estimated using bounded nonlinear least-squares circle fitting.

The measurement module evaluates:

- Candidate cylindrical-wall point count
- Circle-fitting RMSE
- Fitted parameter bounds
- Angular observation coverage
- Largest unobserved angular sector gap

A controlled partial-occlusion experiment demonstrated that point count alone is insufficient.

A synthetic test containing 78 densely concentrated observations passed the point-count requirement but covered only 50% of the hole circumference.

The angular-coverage gate correctly returned REVIEW.

### Repeatability experiments

Twenty fixed-registration trials with additional Gaussian coordinate noise were performed.

| Metric | Hole 1 | Hole 2 |
|---|---:|---:|
| Mean measured diameter | 4.99771 mm | 5.01966 mm |
| Sample standard deviation | 0.01365 mm | 0.02071 mm |
| Successful measurements | 20/20 | 20/20 |

These statistics describe conditional synthetic repeatability, not complete sensor uncertainty.

The project also investigates the distinction between circle-fitting residuals, measurement repeatability, registration accuracy, and dimensional deviation from nominal CAD.

## 4. Geometric Defect Detection

The synthetic inspection pipeline computes geometric deviations and identifies spatial clusters using DBSCAN.

Detected candidate defects are summarized by:

- Cluster identifier
- Number of points
- Spatial center
- Maximum absolute deviation
- Mean absolute deviation

A colored PLY visualization highlights regions exceeding an exploratory deviation threshold.

Cluster point counts are not interpreted as physical defect area.

## 5. Real-World 3D Scan Experiment

The pipeline's registration and deviation-analysis methods were also evaluated using real scan data from **Real3D-AD**.

A normal candybar scan (`137_good.ply`) and a defective candybar scan (`347_bulge.ply`) were compared against a reference template (`123_template.ply`).

The real-data experiment uses point-cloud-to-point-cloud registration and nearest-neighbor surface-distance analysis, rather than the L-bracket's CAD-specific feature inspection.

### Real-data results

| Metric | Normal scan | Bulge-labeled scan |
|---|---:|---:|
| ICP fitness | 1.000 | 1.000 |
| Median reference distance | 0.06763 | 0.06668 |
| Largest DBSCAN cluster | 225 points | 297 points |
| Largest cluster mean deviation | 0.2116 | 0.4981 |
| Largest cluster maximum deviation | 0.2437 | 0.7943 |

Distances are reported in dataset coordinate units.

The bulge-labeled scan contained a substantially stronger localized high-deviation cluster, despite having a global median distance similar to the normal scan.

This demonstrates the value of localized anomaly analysis over relying exclusively on global registration statistics.

**Limitation:** The detected clusters were not evaluated against point-level ground-truth anomaly masks. These results demonstrate exploratory anomaly localization, not validated defect segmentation.

## 6. Project Structure

```text
Scan-to-CAD-System/
├── main.py
├── requirements.txt
├── pytest.ini
├── configs/
│   └── inspection_config.json
├── src/
│   ├── geometry.py
│   ├── registration.py
│   ├── registration_multistart.py
│   ├── features.py
│   ├── inspection.py
│   ├── defects.py
│   ├── reporting.py
│   └── run_pipeline.py
├── tests/
│   ├── test_geometry.py
│   ├── test_inspection.py
│   ├── test_registration_quality.py
│   ├── test_pipeline_smoke.py
│   └── test_cli.py
├── data/
│   ├── nominal/
│   └── synthetic/
├── benchmarks/
└── outputs/  # Generated locally
```

Downloaded real-world datasets and generated outputs are excluded from version control.

## 7. Installation

The project was developed and tested in Google Colab using Python 3.13 and Open3D 0.20.0.

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/3d-scan-to-cad-inspection.git
cd 3d-scan-to-cad-inspection
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it, then install dependencies:

```bash
python -m pip install -r requirements.txt
```

Installation on other Python versions and operating systems has not yet been independently verified.

## 8. Running an Inspection

Once the example CAD and scan files have been placed in the expected directories, execute:

```bash
python main.py \
  --cad data/nominal/bracket.stl \
  --scan data/synthetic/raw_scan.ply \
  --config configs/inspection_config.json \
  --output outputs/demo
```

The program generates:

- `inspection_report.json` — registration diagnostics, feature measurements, tolerance decisions, and defect-cluster summaries.
- `deviation_cloud.ply` — colored point cloud representing unsigned geometric deviations, when inspection proceeds.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Inspection PASS |
| 1 | Inspection FAIL |
| 2 | Inspection REVIEW |

Nonzero exit codes 1 and 2 represent inspection outcomes, not necessarily Python execution failures.

## 9. Automated Testing

The project includes automated tests for geometry loading, tolerance evaluation, registration diagnostics, end-to-end pipeline execution, and command-line behavior.

Run:

```bash
python -m pytest tests/ -v
```

Latest tested result:

**20 tests passed in 25.77 seconds.**

The test suite includes integration smoke tests but does not yet provide comprehensive geometric accuracy regression coverage.

## 10. Known Limitations

This project is a research and engineering prototype.

Current limitations include:

- Synthetic scanner data for the CAD-based dimensional inspection benchmark.
- Demonstration tolerances rather than production drawing requirements.
- L-bracket-specific feature segmentation and datum assumptions.
- Sensitivity of FPFH/RANSAC registration to ambiguous geometry.
- Feature-aware validation may return REVIEW for correctly aligned but occluded features.
- Circle-fitting bias when selected wall points contain distorted or unrelated geometry.
- Angular coverage does not guarantee geometric measurement accuracy.
- Incomplete calibrated measurement uncertainty budget.
- Simplified flange deviation and flatness proxies rather than complete GD&T evaluation.
- Real-data anomaly localization without point-level ground-truth segmentation validation.
- No physical scanner calibration or production deployment validation.

## 11. Future Improvements

Potential extensions include:

- Independent reference-feature and datum validation
- More robust cylindrical-wall segmentation
- Tilted-cylinder and 3D primitive fitting
- Measurement uncertainty and tolerance guard-banding
- Registration failure-rate evaluation across multiple parts and scans
- Surface-coverage analysis
- Ground-truth anomaly-mask evaluation
- Additional real-world scan-to-CAD datasets
- Automated inspection dashboards

## Technologies

Python · Open3D · NumPy · SciPy · Pandas · Matplotlib · Plotly · pytest · Git

## Data and Attribution

The nominal L-bracket model was obtained from [Simple L Bracket on Printables](https://www.printables.com/model/199710-simple-l-bracket).

The real-world point-cloud experiment uses the [Real3D-AD dataset](https://openreview.net/pdf?id=zGthDp4yYe).

Third-party CAD and scan data are subject to their respective licenses and redistribution terms. Users should obtain the original assets from their authorized sources where redistribution is not permitted.

---

**Project focus:** Building a reproducible 3D inspection workflow while investigating registration ambiguity, measurement reliability, geometric defect detection, and the limitations of real-world point-cloud analysis.
