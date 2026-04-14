# Urine Drug Screen Interpretation Labeling Tool

Tool for automatically labeling urine drug screen
interpretation text. Uses a DeBERTa-based zero-shot classifier
(`MoritzLaurer/deberta-v3-large-zeroshot-v1.1-all-33`) to assign a per-substance
numeric label to each interpretation.

This tool is intended to run using clinically generated interpretations for UDTs, 
to generate training data for the models used in the interpret function. 
However, to test functionality, use label.py to first generate interpretations for the

---

## Installation

```bash
pip install -r requirements.txt
```

The DeBERTa model (~900 MB) is downloaded automatically from HuggingFace on first
run and cached locally. Subsequent runs use the cached copy.

If the machine cannot reach HuggingFace (e.g. behind a firewall), set the
environment variable `HF_HUB_OFFLINE=1` after the model has been cached once:

```bash
HF_HUB_OFFLINE=1 python label.py --csv interpretations.csv
```

---

## Usage

### Batch mode (CSV input)

```bash
python label.py \
    --csv   interpretations.csv \
    --output labeled.csv \
    --interp-colname Interpretation \
    --threads 4
```

### Single-string mode (quick test)

```bash
python label.py --interpretation "These results are consistent with buprenorphine therapy."
```

### All arguments

| Argument | Default | Description |
|---|---|---|
| `--csv` | `interpretations.csv` | Input CSV file (batch mode) |
| `--output` | `labeled.csv` | Output CSV file |
| `--interp-colname` | `Interpretation` | Column name containing interpretation text |
| `--ordx-colname` | `ordx` | Optional order-ID column; a sequential `ID` is used if absent |
| `--threads` | all available | Number of PyTorch CPU threads |
| `--row-limit` | `-1` (all) | Maximum number of rows to process |
| `--start-offset` | `0` | Row index to start from (for resuming an interrupted run) |
| `--interpretation` | — | Single interpretation string; prints result to console only |

---

## Output format

The output CSV contains all original columns plus:

| Column | Type | Description |
|---|---|---|
| `Z_BUPR` | 0–3 | Buprenorphine label |
| `Z_FENT` | 0–3 | Fentanyl label |
| `Z_MAMP` | 0–3 | Methamphetamine label |
| `Z_AMP` | 0–3 | Amphetamine label |
| `Z_COC` | 0–3 | Cocaine label |
| `Z_CANB` | 0–3 | Cannabinoids label |
| `Z_METH` | 0–3 | Methadone label |
| `Z_OCOD` | 0–3 | Oxycodone label |
| … | 0–3 | One column per substance (see label mapping below) |
| `Z_INVALID` | 0/1 | Sample validity flag (1 = possible adulteration) |
| `json` | String | Raw per-substance classifier scores |

### Label mapping

| Value | Meaning |
|---|---|
| `0` | Negative |
| `1` | Positive |
| `2` | False positive |
| `3` | Distant use |

### Full substance code list

`Z_ALC`, `Z_ALPR`, `Z_AMP`, `Z_BARB`, `Z_BUPR`, `Z_CANB`, `Z_CLON`, `Z_COC`,
`Z_COD`, `Z_DIAZ`, `Z_FENT`, `Z_HCOD`, `Z_HER`, `Z_HMOR`, `Z_LORA`, `Z_MAMP`,
`Z_MDMA`, `Z_METH`, `Z_MORP`, `Z_MPH`, `Z_OCOD`, `Z_OXYM`, `Z_POXY`, `Z_TRAM`,
`Z_TEMA`
