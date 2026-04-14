"""
Standalone script for generating a textual interpretation for urine drug testing results.

General flow: 
1. Reads a CSV file containing results of immunoassay and/or confirmatory testing
2. Parses an input UEXPD (expected drug list) text string, to convert it to a binary vector
3. Passes all inputs to a series of XGBoost models, to predict usage of different substances
4. Passes outputs of those models to a text generation process.

Written by Brody H Foy, and Nathan Laha, 2026. 
Contact: Dr Brody H Foy, University of Washington Medicine, Department of Laboratory Medicine &
Pathology. brodyfoy@uw.edu

Usage:
    python interpret.py --input  cases.csv --output interpretations.csv --models models_dir

Input CSV columns:
    - Screen result codes: UOPIQL, UBNZQL, UAMTQL, UTHCQL, UCOCQL, UBUPQL,
                           UFENQL, UMDNQL, UOXCQL, UTRAQL, UBRBQL, UETOH, UETG
    - Confirmatory codes:  UBUPR, UHCOD, UFENT, UOXCD, UAHALP, UAMP, UMA, etc.
    - UEXPD (optional):    free-text field listing expected/prescribed substances
    - UBATT (optional):    ordering battery code (e.g. UCPD1C, UAMPC); controls which
                           categories are included/excluded from the interpretation
    - M-codes (optional):  Manual binary codes for expected substances. If absent, will be derived from UEXPD
    - Any column not present defaults to -2 (missing data).

Output CSV:
    Original columns plus an "Interpretation" column.
"""
# General library imports
import argparse
import sys
import os
import pandas as pd

# Ensure the bundled classifier/ package takes priority over any installed
# version of the same name, regardless of the working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Import classifier scripts
from classifier.predict import load_models, predict          
from classifier.preprocess import preprocess                
from classifier.uexpd_parser import parse_uexpd              
from classifier.interpretation import Interpretation         

def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Generate urine drug screen interpretations from lab result CSVs"
    )
    p.add_argument("--input",  required=True,
                   help="Input CSV path")
    p.add_argument("--output", default="interpretations.csv",
                   help="Output CSV path (default: interpretations.csv)")
    p.add_argument("--models", required=True,
                   help="Directory containing *.joblib model files")
    return p


def row_to_dict(row: pd.Series) -> dict:
    """Convert a DataFrame row to a plain Python dict, dropping NaN values."""
    return {k: v for k, v in row.to_dict().items() if pd.notna(v)}


def main():
    args = build_arg_parser().parse_args()

    # ------------------------------------------------------------------
    # Load models
    # ------------------------------------------------------------------
    models_path = os.path.abspath(args.models)
    print(f"Loading models from {models_path} ...")
    load_models(models_path)

    # ------------------------------------------------------------------
    # Read input CSV
    # ------------------------------------------------------------------
    print(f"Reading {args.input} ...")
    data = pd.read_csv(args.input, dtype=str)
    # Convert numeric columns to float; leave UEXPD and UBATT as strings.
    # pd.to_numeric errors="ignore" was removed in pandas 2.0, so use try/except
    # to replicate the same behaviour: leave non-numeric columns unchanged.
    for col in data.columns:
        if col not in ("UEXPD", "UBATT"):
            try:
                data[col] = pd.to_numeric(data[col])
            except (ValueError, TypeError):
                pass
    print(f"  {len(data):,} rows, {len(data.columns)} columns\n")

    interpretations = []

    # Iterate through and create interpretations
    for idx, row in data.iterrows():
        patient_results = row_to_dict(row)

        # 1. Translate legacy codes / apply unit conversions
        patient_results = preprocess(patient_results)

        # 2. Parse UEXPD free-text -> expected M-code flags (e.g. buprenorphine -> MBPRN=1)
        uexpd_text = str(patient_results.get("UEXPD", ""))
        expected_from_uexpd = parse_uexpd(uexpd_text)
        for m_code, flag in expected_from_uexpd.items():
            if m_code not in patient_results:
                patient_results[m_code] = flag

        # 3. Run ML models to generate substance use predictions
        predictions = predict(patient_results)

        # 4. Extract battery/order codes from the UBATT column (if present),
        #    then remove it so it doesn't pollute patient_results for the interpretation.
        ubatt_val = patient_results.pop("UBATT", None)
        extra_ordered_codes = {str(ubatt_val)} if ubatt_val is not None else set()

        # 5. Use predictions to generate interpretation text
        interp = Interpretation(
            predict_results=predictions,
            patient_results=patient_results,
            extra_ordered_codes=extra_ordered_codes,
        )
        interp_text = str(interp)
        interpretations.append(interp_text)

        print(f"Row {idx + 1}/{len(data)}: {interp_text[:100]}{'...' if len(interp_text) > 100 else ''}")

    # ------------------------------------------------------------------
    # Write output back to csv
    # ------------------------------------------------------------------
    out = data.copy()
    out["Interpretation"] = interpretations
    out.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
