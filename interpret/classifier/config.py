from itertools import chain
import yaml
import os
import logging

PROFILE_NAME = "default"

TARGET_MAPPINGS = None
PROFILE = None

# Load YAML config files into global variables
try:
    with open(os.path.join(os.path.dirname(__file__), "config/target_mappings.yaml"), "r", encoding="utf-8") as file:
        TARGET_MAPPINGS = yaml.safe_load(file)

    with open(os.path.join(os.path.dirname(__file__), f"config/profiles/{PROFILE_NAME}.yaml"), "r", encoding="utf-8") as file:
        PROFILE = yaml.safe_load(file)
except yaml.YAMLError:
    logging.error("Error loading config file for interpretation generator")


targets = list(TARGET_MAPPINGS['targets'].values())
category_targets = list(TARGET_MAPPINGS['category_targets'].values())

CONFIRM_CODES = list(chain(*map(lambda t: t['confirm'], targets)))
SCREEN_CODES = list(chain(*map(lambda t: t['screen'], targets)))
EXPECTED_CODES = list(map(lambda t: t['expected'], targets))
EXPECTED_CODES_W_SECONDARY = EXPECTED_CODES + list(chain(*map(lambda t: t['secondary_expected'] if 'secondary_expected' in t else [], targets)))

CAT_EXPECTED_CODES = list(chain(*map(lambda t: t['expected'], category_targets)))
