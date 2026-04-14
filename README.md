# Urine Drug Screen Interpretation Tool
Tool for generating textual interpretations of urine drug testing results. 
There are two components to the codebase:
1) A labeling script, which takes in textual interpretations and uses
a zero-shot LLM to convert them to structured labels of substance use.
2) An interpretation script, which takes in immunoassay and confirmatory
test results, and creates a textual interpretation based on them.

These files are based on work in the publication: 
Laha N, et al. Development and implementation of an AI system for clinical toxicology sign-outs. medRxiv. 2026.
https://www.medrxiv.org/content/10.64898/2026.01.29.26345133v1

**Authors:** Brody H Foy, Nathan Laha — University of Washington Medicine,
Department of Laboratory Medicine & Pathology (2026).

**Contact:** Dr Brody H Foy. University of Washington Medicine, Department of Laboratory Medicine & Pathology. brodyfoy@uw.edu

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage (Interpreter)

```bash
python interpret/interpret.py --input synthetic_cases.csv --output interpretations.csv --models  interpret/models
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `--input` | Yes | — | Path to input CSV |
| `--output` | No | `interpretations.csv` | Path to output CSV |
| `--models` | Yes | — | Directory containing `*.joblib` model files |

The output CSV contains all original columns plus an added `Interpretation` column.

---

## Usage (Labeler)

```python label.py --csv --interpretations.csv --interp-colname Interpretation ```

---

## Test results data structure

All result columns use the following encoding:

| Value | Meaning |
|---|---|
| `-2` | Test not run / not ordered |
| `0` | Run, result negative |
| positive number | Quantitative result (ng/mL or immunoassay units) |

Columns not present in the CSV are treated as `-2` (not run).

### Immunoassay screen codes

| Code | Test |
|---|---|
| `UOPIQL` | Opioids |
| `UBUPQL` | Buprenorphine |
| `UBNZQL` | Benzodiazepines |
| `UAMTQL` | Amphetamines |
| `UTHCQL` | Cannabinoids |
| `UCOCQL` | Cocaine |
| `UFENQL` | Fentanyl |
| `UMDNQL` | Methadone |
| `UOXCQL` | Oxycodone |
| `UTRAQL` | Tramadol |
| `UBRBQL` | Barbiturates |
| `UETOH` | Ethanol |
| `UETG` | Ethyl glucuronide |

### Confirmatory (mass spectrometry) codes:

Opioids: `UBUPR`, `UNBUPG`, `UCOD`, `UCOD6G`, `UFENT`, `UFENTM`, `UHCOD`,
`UNHCOD`, `UHMOR`, `UHMORG`, `UMETH`, `UEDDP`, `UMOR3G`, `UMOR6`, `UMOR6G`,
`UMORPH`, `UOXCD`, `UTRMQL`, `UOXYM`, `UOXYMG`, `UMPER`, `UMPERM`, `UPPOX`

Benzodiazepines: `UAHALP`, `U7ACZ`, `UNDAZ`, `ULORZ`, `UTEMZ`, `UAHTZM`,
`UDFRZ`, `U7AFZ`, `UOXAZ`, `U2FRZP`

Amphetamines: `UAMP`, `UMA`, `URITAL`, `UMDMA`, `UMDA`

### Optional columns

| Column | Type | Description |
|---|---|---|
| `UEXPD` | String | Free-text list of prescribed/expected substances (e.g. `"buprenorphine, oxycodone"`). Parsed automatically to set expected-substance flags. |
| `UBATT` | String | Ordering battery code. Controls which substance categories are always included or excluded from the interpretation, regardless of result. See battery codes below. |
| `MAMPH`, `MBPRN`, … | Integer (0/1) | Expected-substance M-codes. Set to `1` if expected. If absent, derived from `UEXPD`. |

### Battery codes (`UBATT`)

| Code | Effect on interpretation |
|---|---|
| `UCPD1C` | Always include Opioids category |
| `UCPD2C` | Always include Alcohol and Opioids |
| `UCPD3C` | Always include Alcohol, Opioids, and Benzodiazepines |
| `UCPD4C` | Always include Opioids; suppress Cannabinoids if expected but not in panel |
| `UOPIAC` | Always include Opioids |
| `UAMPC` | Always include Amphetamines |
| `UBNZC` | Always include Benzodiazepines |
| `UCETOH` | Always include Alcohol |
| `UPDRS2` | Suppress Cannabinoids if expected but not in panel |

"Always include" means that if all substances in that category are negative, the
interpretation will explicitly state so (e.g. *"There is no evidence for the use of
opioids"*) rather than remaining silent.

---

## Synthetic data
To test the code base, use the file synthetic_data.csv. First run:

```python interpret.py --input synthetic_cases.csv --output interpretations.csv --models  models```


to generate interpretations.

Then run: 

```python label.py --csv --interpretations.csv --interp-colname Interpretation ```


to convert the interpretations to quantitative targets
