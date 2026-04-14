import re
from thefuzz import fuzz
import numpy as np

## The UEXPD parser uses a combination of exact string matching, and fuzzy string matching
# First we define exact string matches to convert to specific substances
UEXPD_EXACT_MAPPING = {
    'MAMPH': {'AMP', 'TAMP', 'TMAMP'},
    'MBARB': {},
    'MALPR': {'ALPR', 'TALPR'},
    'MDIAZ': {'TDIAZ'},
    'MTEMA': {},
    'MTRIA': {'TTRAZ', 'TTRIAZ'},
    'MBPRN': {'BUPR', 'TBUPR', 'TBUPN', 'BUP', 'BUPREN', 'BURP'},
    'MMARI': {'THC', 'TTHC', 'MJ'},
    'MCOCA': {'TCOC', 'COC'},
    'MFENT': {'FENT', 'TFENT'},
    'MMETH': {'TMETH', 'METH', 'EDDP'},
    'MCODN': {'TCOD', 'COD'},
    'MHERO': {},
    'MHCOD': {'THCOD', 'HCOD'},
    'MHMOR': {'THMOR', 'HMOR'},
    'MMORP': {'TMOR', 'MOR', 'TMORPH'},
    'MOXYC': {'TOXY', 'OXY', 'TOXCD'},
    'MOXYM': {},
    'MTRAM': {'TRAM', 'TTRAM'},
    'MBPRO': {},
    'MPHEN': {},
    'MPROP': {},
    'MCLON': {'TCLZP', 'TCLON', 'TCLPZ'},
    'MLORA': {'TLOR'},
    'MMPHEN': {},
    'MOPIA': {},
    'MBENZ': {},
    'MALCO': {'ETOH'},

    # not used in model, but helpful for interpretation generation.
    'MAMP': {'AMP'},
    'MMAMP': {'UMA'}
}

# These are the strings we fuzzy match
UEXPD_FUZZY_MAPPING = {
    'MAMPH': {
        'amphetamine', 'adderall', 'methamphetamine', 'dextroamphetamine', 'meth',
        'dextromethamphetamine', 'dextoramphet', 'lisdexamfetamine', 'vyvanse', 'lisdexamphetamin'
    },
    'MBARB': {'butabarbital', 'butalbital', 'fioricet', 'fiorinal', 'pentobarbital', 'primidone', 'barbital', 'barbiturate'},
    'MALPR': {'alprazolam', 'xanax'},
    'MDIAZ': {'diazepam', 'valium'},
    'MTEMA': {'temazepam'},
    'MTRIA': {'triazolam'},
    'MBPRN': {'buprenorphine', 'suboxone', 'sublocade', 'butrans', 'norburphrenorphine'},
    'MMARI': {'marijuana', 'cannabis', 'cannabinoids', 'cannabidiol', 'cannibus', 'dronabinol', 'marinol'},
    'MCOCA': {'cocaine'},
    'MFENT': {'fentanyl'},
    'MMETH': {'methadone'},
    'MCODN': {'codeine', 'dihydrocodeine'},
    'MHERO': {'heroin'},
    'MHCOD': {'hydrocodone', 'vicodin', 'norco'},
    'MHMOR': {'hydromorphone', 'dilaudid'},
    'MMORP': {'morphine', 'diacetylmorphine'},
    'MOXYC': {'oxycodone', 'oxycontin', 'percocet'},
    'MOXYM': {'oxymorphone'},
    'MTRAM': {'tramadol'},
    'MBPRO': {'bupropion', 'wellbutrin'},
    'MPHEN': {'phentermine'},
    'MPROP': {'propranolol'},
    'MCLON': {'clonazepam', 'clonazapine', 'klonopin'},
    'MLORA': {'lorazepam', 'ativan'},
    'MMPHEN': {'methylphenidate', 'ritalin', 'concerta'},
    'MOPIA': {'opiates', 'opioids', 'meperidine'},
    'MBENZ': {
        'BENZODIAZEPINE', 'BENZO', 'BENZOPINES', 'BENZODIAPAM', 'eitzolam', 'estazolam',
        'nitrazepam', 'oxazepam', 'clorazepate', 'midazolam', 'flunitrazepam', 'CHLORDIAZEPOXIDE', 'Librium'
    },
    'MALCO': {'alcohol'},

    # not used in model, but helpful for interpretation generation.
    'MAMP': {
        'amphetamine', 'adderall', 'dextroamphetamine', 'dextromethamphetamine',
        'dextoramphet', 'lisdexamfetamine', 'vyvanse', 'lisdexamphetamin'
    },
    'MMAMP': {
        'methamphetamine',
        'meth'
    }
}


def parse_uexpd(uexpd: str) -> dict:
    """
    Parses the UEXPD code result into a dictionary of
    drugs/substance and whether they are expected
    """

    if type(uexpd) is not str:
        return

    # remove basic punctuation
    p_re_basic = re.compile(r'[,./")(-]')
    uexpd = p_re_basic.sub(' ', uexpd)

    # tokenize into words and remove duplicates
    words = set(re.findall(r'\w+', uexpd))
    # convert to lowercase
    words = set(map(lambda x: x.lower(), words))

    # remove common words that map closely to a medication name (e.g., iodine v codeine)
    words.difference(set(['concern', 'determine', 'iodine', 'lithium', 'nor']))

    output = {}

    # iterate through all output codes
    # and see if the string has matches
    out_codes = set(UEXPD_FUZZY_MAPPING.keys())
    for out_code in out_codes:
        mappings = UEXPD_FUZZY_MAPPING[out_code]
        # loop through each alias (mapping) for the out code
        for mapping in mappings:
            mapping = mapping.lower()
            # for each mapping, check the distance to each word
            for word in words:
                ratio = fuzz.token_sort_ratio(word, mapping)
                # Vary the threshold by complexity (word length)
                threshold = 90
                if len(word) > 8:
                    threshold = 85
                if ratio > threshold:
                    output[out_code] = 1
        # check for any exact matches as well
        exact_mappings = set(map(lambda x: x.lower().strip(), UEXPD_EXACT_MAPPING[out_code]))
        if (len(words.intersection(exact_mappings)) > 0):
            output[out_code] = 1

    return output

if __name__ == '__main__':
    # load test data
    import pandas as pd
    test_data = pd.read_csv('uexpd_test.csv')

    for idx, row in test_data.iterrows():
        parse_uexpd(row['UEXPD'])
