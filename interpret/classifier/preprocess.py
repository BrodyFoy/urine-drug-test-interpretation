from classifier.config import TARGET_MAPPINGS

def preprocess(result_dict: dict):
    """
        Preprocesses results, handles converting new codes into
        ones the model can understand - also multiplies results to handle unit changes
    """

    translations = TARGET_MAPPINGS['code_translations']

    for new_code, mapping in translations.items():
        if new_code in result_dict:
            try:
                # Check if the new code is numeric, and if so, scale it appropriately and map to the new code
                numeric_val = float(result_dict[new_code])
                result_dict[mapping['target_code']] = str(numeric_val / mapping['multiplier'])
            except ValueError:
                # If non-numeric, just map to the new code
                result_dict[mapping['target_code']] = result_dict[new_code]
        
    return result_dict
