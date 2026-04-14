# Script for extracting labels from substance use interpretation notes
# This file uses a BERTa zero-shot model to label, based on matching
# to typical language used within our urine drug testing service. 
#
# use with data from other services should be done with caution, and after validation
# of accuracy for these different contexts
#
# Written by Brody H Foy, and Nathan Laha
# Contact: Dr Brody H Foy, University of Washington Medicine, Department of Laboratory Medicine & Pathology
# email: brodyfoy@uw.edu
# 
# Usage:
#     python label.py --csv interpretations.csv --output labeled.csv \
#                     --interp-colname Interpretation --threads 4
# (threads controls multi-threading for efficiency)
# Input CSV must have a column containing interpretation text (default: "Interpretation").
# An "ordx" (order number) column is optional; if absent a sequential ID is used instead.
#
# Output CSV: original columns + one Z_* column per substance (0-3) + "json" raw scores.
# Labels are: 0=negative, 1=positive, 2=false positive, 3=distant/low-dose use
#
# Flow/process:
# 1. The interpretation is broken down into individual sentences.
# 2. Fuzzy string matching is used to identify which sentences mention a given substance
# 3. Each mentioning sentence is passed to the BERT model, which calculates whether the sentence
# is consistent with X of Y, where Y is the substance, and X is the typical phrasing of a label
# (i.e., expected use of buprenorphine, or no evidence for cocaine, etc.)
# 4. The substance label is taken as the highest overall model probability across all model runs
# and all relevant sentences in the interpretation.


import functools
import itertools
import operator
import os
import pandas as pd
import re
import torch
from transformers import pipeline
from colorama import Fore, Back, Style
from thefuzz import fuzz
import nltk
from collections import defaultdict
import json
import argparse
import csv


# Mapping of substance names (as they typically appear in interpretation text) to short codes.
INTERP_SUBSTANCE_TABLE = {
    "alcohol": "ALC",
    "barbiturate": "BARB",
    "butalbital": "BARB",
    "phenobarbital": "BARB",
    "pentobarbital": "BARB",
    "barbital": "BARB",
    "butabarbital": "BARB",
    "primidone": "BARB",
    "cocaine": "COC",
    "cannabinoid": "CANB",
    "marijuana": "CANB",
    "dronabinol": "CANB",
    "cannabis": "CANB",
    "benzodiazepine": "BENZ",
    "chlordiazepoxide": "BENZ",
    "midazolam": "BENZ",
    "clorazepate": "BENZ",
    "flunitrazepam": "BENZ",
    "amphetamine": "AMP",
    "lisdexamfetamine": "AMP",
    "dextroamphetamine": "AMP",
    "methamphetamine": "MAMP",
    "dextromethamphetamine": "MAMP",
    "mdma": "MDMA",
    "methylphenidate": "MPH",
    "hydromorphone": "HMOR",
    "hydrocodone": "HCOD",
    "morphine": "MORP",
    "diacetylmorphine": "MORP",
    "heroin": "HER",
    "meperidine": "MEPR",
    "oxycodone": "OCOD",
    "propoxyphene": "POXY",
    "buprenorphine": "BUPR",
    "codeine": "COD",
    "dihydrocodeine": "COD",
    "fentanyl": "FENT",
    "tramadol": "TRAM",
    "methadone": "METH",
    "clonazepam": "CLON",
    "flurazepam": "FLUR",
    "alprazolam": "ALPR",
    "triazolam": "TRIA",
    "lorazepam": "LORA",
    "diazepam": "DIAZ",
    "temazepam": "TEMA",
    "oxymorphone": "OXYM",
}

# Lists of typical phrasing used in the interpretations, and their associated mapping
# to substance labels
LABEL_MAPPING = {
    "evidence for use or positive": 1,
    "consistent with prescribed therapy": 1,
    "unknown or inconclusive": 0,
    "no evidence for recent use or negative": 0,
    "from another substance as a metabolite or contaminant": 0,
    "false positive": 2,
    "distant, or low dose (low_dose)": 3,
    "below the limit of quantification": 3,
    "consistent with low dose or distant use": 3,
    "minute quantity": 3,
    "consistent with distant use": 3,
}

# Used to identify if a sentence mentions a given substance
def fuzzy_match_substance(substance, interpretation):
    """Return the highest fuzzy match ratio for a substance name in interpretation text."""
    max_ratio = 0
    for word in interpretation.lower().split(" "):
        ratio = fuzz.ratio(word, substance.lower())
        if ratio > max_ratio:
            max_ratio = ratio
    return max_ratio

# Calculates the average model score for each overall label
def average_by_first_value(tuples_list):
    """Group (label, score) tuples by label and return mean score per label."""
    avg = defaultdict(lambda: {"count": 0, "sum": 0})
    for k, v in tuples_list:
        avg[k]["count"] += 1
        avg[k]["sum"] += v
    return [(k, v["sum"] / v["count"]) for k, v in avg.items()]

## Runs the classifier model on the hypothesis, matched to the sentence
def classify(candidate_labels, out, interpretation):
    """Run zero-shot classifier and accumulate per-substance label scores into out."""
    classified = classifier(
        interpretation,
        candidate_labels,
        hypothesis_template="Therefore test result for {}.",
        multi_label=True,
    )
    classified_tuples = [
        (classified["labels"][i], x) for i, x in enumerate(classified["scores"])
    ]
    for t in classified_tuples:
        substance = t[0].split(" is: ")[0]
        if substance not in out:
            out[substance] = []
        out[substance].append((" ".join(t[0].split(" is: ")[1:]), t[1]))


if __name__ == "__main__":
    print("Starting...")

    parser = argparse.ArgumentParser(
        prog="Assay Interpretation Classifier",
        description="Labels drug assay interpretations per substance using zero-shot classification",
    )
    parser.add_argument("--interpretation", required=False,
                        help="Single interpretation string (ad-hoc testing mode)")
    parser.add_argument("--csv", required=False, default="interpretations.csv",
                        help="Input CSV file (batch mode)")
    parser.add_argument("--threads", required=False,
                        default=torch.get_num_threads(), type=int,
                        help="Number of PyTorch threads")
    parser.add_argument("--output", required=False, default="labeled.csv",
                        help="Output CSV file")
    parser.add_argument("--row-limit", required=False, default=-1, type=int,
                        help="Max rows to process (-1 = all)")
    parser.add_argument("--start-offset", required=False, default=0, type=int,
                        help="Row index to start from (for resuming)")
    parser.add_argument("--interp-colname", required=False, default="Interpretation",
                        help="Name of the interpretation text column in the input CSV")
    parser.add_argument("--ordx-colname", required=False, default="ordx",
                        help="Name of the order-index column (optional; sequential ID used if absent)")
    args = parser.parse_args()

    torch.set_num_threads(args.threads)
    print(f"Threads: {args.threads}")

    # ------------------------------------------------------------------
    # Load input
    # ------------------------------------------------------------------
    interps_clean = pd.DataFrame()
    if args.interpretation:
        print("Single interpretation mode.")
        interps_clean = pd.DataFrame({"ID": [0], args.interp_colname: [args.interpretation]})
    else:
        print(f"Batch mode: reading {args.csv}")
        interps_clean = pd.read_csv(args.csv, dtype={args.interp_colname: "string"})
        interps_clean = interps_clean.dropna(subset=[args.interp_colname])

    total_rows = len(interps_clean) if args.row_limit <= 0 else args.row_limit
    print(f"Total rows to process: {total_rows}")

    # Drop any pre-existing Z_* columns from input to avoid conflicts
    interps_clean = interps_clean[
        interps_clean.columns.drop(list(interps_clean.filter(regex="^Z_")))
    ]

    # Ensure ID column
    if "ID" not in interps_clean.columns:
        interps_clean["ID"] = range(len(interps_clean))

    # Determine whether ordx column exists
    has_ordx = args.ordx_colname in interps_clean.columns

    # ------------------------------------------------------------------
    # Load zero-shot model
    # ------------------------------------------------------------------
    classifier = pipeline(
        "zero-shot-classification",
        model="MoritzLaurer/deberta-v3-large-zeroshot-v1.1-all-33",
    )

    # ------------------------------------------------------------------
    # Build output column set
    # ------------------------------------------------------------------
    colnames = set(f"Z_{code}" for code in set(INTERP_SUBSTANCE_TABLE.values()))
    colnames.update({"Z_INVALID", "ID", args.interp_colname, "json"})
    if has_ordx:
        colnames.add(args.ordx_colname)
    colnames = colnames.union(set(interps_clean.columns))
    colnames = sorted(colnames)

    # Remove existing output file so we write a fresh one
    if os.path.exists(args.output):
        print(f"Removing existing output: {args.output}")
        os.remove(args.output)

    data_index = args.start_offset

    # ------------------------------------------------------------------
    # Main processing loop
    # ------------------------------------------------------------------
    while True:
        interpretation_full = str(interps_clean[args.interp_colname].iloc[data_index])
        row_id = interps_clean["ID"].iloc[data_index]

        # Normalize text
        interpretation_full = interpretation_full.replace("/", " ")
        interpretation_full = re.sub(r" +", " ", interpretation_full).replace("\n", "")

        # Sentence tokenize
        sentences = nltk.regexp_tokenize(
            interpretation_full, pattern=r"[.](?:\s+|$)", gaps=True
        )

        out = {}
        for sentence in sentences:
            if not sentence.strip():
                continue

            substances = [
                s for s in INTERP_SUBSTANCE_TABLE
                if fuzzy_match_substance(s, sentence) > 90
            ]
            if not substances:
                continue

            candidate_labels = [
                " is: ".join(pair)
                for pair in itertools.product(substances, LABEL_MAPPING.keys())
            ]
            classify(candidate_labels, out, sentence)

        # Average scores across sentences for the same substance
        for substance in out:
            out[substance] = average_by_first_value(out[substance])
            out[substance].sort(key=lambda x: x[1], reverse=True)

        # Console output
        print(f"\nRow {data_index + 1}/{total_rows}: {interpretation_full[:100]}")
        for key, value in out.items():
            print(f"  {key}: {value[0][0]} ({value[0][1]:.3f})")

        # Build output row
        interp_results = dict.fromkeys(colnames, None)
        interp_results["json"] = json.dumps(out)
        interp_results["ID"] = row_id

        if has_ordx:
            interp_results[args.ordx_colname] = interps_clean[args.ordx_colname].iloc[data_index]

        # Map substances to Z_* numeric codes
        for substance, scores in out.items():
            z_col = "Z_" + INTERP_SUBSTANCE_TABLE[substance]
            mapped = LABEL_MAPPING[scores[0][0]]
            if interp_results.get(z_col) is None or interp_results[z_col] < mapped:
                interp_results[z_col] = mapped

        interp_results["Z_INVALID"] = 0

        # Validity check
        validity = classifier(
            interpretation_full,
            ["adulterated sample", "valid sample"],
            multi_label=False,
        )
        validity_scores = {
            validity["labels"][i]: s for i, s in enumerate(validity["scores"])
        }
        if validity_scores["adulterated sample"] > validity_scores["valid sample"]:
            print(f"  [INVALID] adulterated confidence: {validity_scores['adulterated sample']:.3f}")
            interp_results["Z_INVALID"] = 1

        # Write to output CSV (append; write header on first row)
        if not args.interpretation:
            interp_results.update(interps_clean.iloc[data_index].to_dict())
            write_header = (data_index == args.start_offset)
            with open(args.output, "a", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(colnames)
                writer.writerow([interp_results.get(c) for c in colnames])

        data_index += 1
        if data_index >= args.start_offset + total_rows:
            break

        print(f"  Next: {data_index}/{total_rows}")

    print(f"\nDone. Output: {args.output}")
