import argparse
import logging
import joblib
import pandas as pd
import xgboost as xgb
import os
from typing import Dict
import hashlib

from classifier.config import CONFIRM_CODES, EXPECTED_CODES, SCREEN_CODES

logger = logging.getLogger(__name__)

# random forest models
MODELS: Dict[str, xgb.XGBClassifier] = {}
MODEL_HASHES: Dict[str, str] = {}

def load_models(path_to_models: str) -> None:
    """
        Loads models from the ./models directory
        into memory (stored in global dicts)
    """
    assert os.path.exists(path_to_models)

    # load models
    for dirpath,_,filenames in os.walk(path_to_models):
        for file in filenames:
            if file.endswith(".joblib"):
                logger.debug(f"Loading confirm model: {file}...")
                model_name = file.replace("_RF.joblib", "")
                MODELS[model_name] = joblib.load(os.path.join(dirpath, file))
                with open(os.path.join(dirpath, file), 'rb') as model_file:
                    MODEL_HASHES[model_name] = hashlib.md5(model_file.read()).hexdigest()

def predict(patient_results: Dict, debug: bool = False) -> Dict:
    """Generates structured interpretation data from a dictionary of expected, screen and confirmatory results

    Args:
        patient_results (Dict): Dictionary of codes and results, i.e. {'MHMOR': 1} (UEXPD is assumed to be parsed out to codes beginning with 'M')

    Returns:
        Dict: A dictionary containing codes and results for the interpretation, i.e. {'Z_COC': 1} or {'Z_CAT_COCAINE': 1} for screen-only inputs
    """
    patient_results_full = patient_results

    for code in CONFIRM_CODES:
        if code not in patient_results:
            patient_results_full[code] = -2
    for code in EXPECTED_CODES:
        if code not in patient_results:
            patient_results_full[code] = -2
    for code in SCREEN_CODES:
        if code not in patient_results:
            patient_results_full[code] = -2

    patient_results = patient_results_full

    logger.info("Processing predictions")
    pred_out = {}
    pred_debuginfo = {}
    models: Dict[str, xgb.XGBClassifier] = MODELS


    for code, model in models.items():
        df_in = pd.DataFrame(patient_results, index=[0])
        for in_code in model.feature_names_in_:
            if in_code not in df_in:
                df_in[in_code] = -2

        df_in_filtered = df_in[model.feature_names_in_]
        pred_out[code] = model.predict(df_in_filtered)[0]
        if debug:
            class_labels = ["NRN", "POS", "DIST"]
            pred_debuginfo[code] = {}
            pred_debuginfo[code]['probabilities'] = [{class_labels[i]: x} for i,x in enumerate(model.predict_proba(df_in_filtered).tolist()[0])]
            pred_debuginfo[code]['xgboost_version'] = xgb.__version__
            pred_debuginfo[code]['model_hash'] = MODEL_HASHES[code]

    for code, pred in pred_out.items():
        logger.info(f"{code}: {pred}")

    if debug:
        return pred_out, pred_debuginfo
    return pred_out
