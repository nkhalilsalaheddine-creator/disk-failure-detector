# disk-failure-detector

A machine learning application that predicts hard disk failures using SMART diagnostic data. Built on a Random Forest classifier trained on the [Backblaze Hard Drive Dataset](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data).

---

## How It Works

```
smartctl (live disk scan)
    → parse SMART attributes into feature row
    → Random Forest Classifier (disk_model.pkl)
    → prediction: Healthy / Failed + confidence + feature breakdown
```

The model was trained on 8,828 balanced instances (4,414 failures + 4,414 healthy) collected from a full year of Backblaze daily snapshots. Overall accuracy: **90.29%**.

---

## Project Structure

```
disk-failure-detector/
├── app/                        # PyQt6 desktop application
│   ├── main.py                 # Entry point
│   ├── main_window.py          # Two-page PyQt6 UI
│   ├── scanner.py              # smartctl subprocess wrapper
│   ├── predictor.py            # Model loader + prediction logic
│   └── requirements.txt        # Python dependencies
│
├── training/                   # ML pipeline notebooks
│   ├── notebooks/
│   │   ├── dataset_acquisition.ipynb   # Builds balanced dataset from raw CSVs
│   │   └── smart_scan_classifier.ipynb # Preprocessing + RF training pipeline
│   └── data/                   # Raw Backblaze CSVs (not tracked by git)
│
├── model/                      # Trained model artifacts
│   ├── disk_model.pkl          # Saved Random Forest classifier
│   └── feature_importance.csv  # Feature importance scores
│
├── docs/
│   └── architecture.txt        # Pipeline and design notes
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Requirements

- Python 3.10+
- [`smartmontools`](https://www.smartmontools.org/) installed on the host machine
  - Linux: `sudo apt install smartmontools`
  - macOS: `brew install smartmontools`
  - Windows: [Download installer](https://www.smartmontools.org/wiki/Download)

---

## Installation

```bash
git clone https://github.com/your-username/disk-failure-detector.git
cd disk-failure-detector

python3 -m venv venv
source venv/bin/activate        

pip install -r app/requirements.txt
```

---

## Usage

```bash
# Make sure disk_model.pkl is in the model/ folder
python app/main.py
```

1. The app auto-detects connected disks via `smartctl --scan`
2. Select a disk and press **SCAN DISK**
3. Results page shows: prediction label, confidence score, and a full SMART attribute breakdown sorted by feature importance

---

## Model Performance

| Metric | Healthy (0) | Failed (1) |
|---|---|---|
| Precision | 88% | 93% |
| Recall | 93% | 87% |
| F1-score | 91% | 90% |

**Overall accuracy: 90.29%**

> Failure recall (87%) is the key metric — 13% of real failures are missed. To improve, consider lowering the classification threshold below 0.5 or tuning `class_weight`.

---

## Training Pipeline

See `training/notebooks/` for the full ML pipeline:

1. **`dataset_acquisition.ipynb`** — scans all Backblaze quarterly CSVs, collects every `failure=1` row, randomly samples an equal number of healthy disks (capped at 20 per file to avoid date bias), outputs `model_ready_data.csv`
2. **`smart_scan_classifier.ipynb`** — full preprocessing (NaN imputation, feature engineering, column filtering) + Random Forest training with GridSearchCV optimization

---

## License

MIT License — see [LICENSE](LICENSE)
