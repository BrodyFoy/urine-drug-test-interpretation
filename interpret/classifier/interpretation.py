from typing import Dict, List, OrderedDict, Set
from classifier.config import CAT_EXPECTED_CODES, CONFIRM_CODES, EXPECTED_CODES_W_SECONDARY, PROFILE, SCREEN_CODES, TARGET_MAPPINGS
from classifier.processors.category_processor import CategoryProcessor
from classifier.processors.false_positive_processor import FalsePositiveProcessor
from classifier.processors.screen_processor import ScreenProcessor
from classifier.processors.shared_expected_processor import SharedExpectedProcessor
from classifier.result import CategoryResult, CodeResult, InterpretationResult, ResultType, SubstanceResult
from classifier.result_collection import ResultCollection
from classifier.utility import FrozenDict, sentence_from_list, subset_dict

class Interpretation:
    """
        Represents the interpretation for a case
    """

    results: ResultCollection

    interpretation = ""

    def generate_interp(self):
        """
            Generates the textual interpretation from the substances
        """

        # run processors
        FalsePositiveProcessor.process(self.results)
        ScreenProcessor.process(self.results)
        SharedExpectedProcessor.process(self.results)
        CategoryProcessor.process(self.results)

        results_ordered: OrderedDict[str, List[InterpretationResult]] = {}

        for key, key_result_type in PROFILE['mappings'].items():
            results_ordered[key] = {}
            for subtype in key_result_type.values():
                results_ordered[key][FrozenDict(subtype)] = []

        for result in self.results.included_results:
            key, key_result_type = result.get_sentence_key()
            if key is None:
                continue
            results_ordered[key_result_type][key].append(result)

        # for each sentence, build the substance lists and output the final
        # sentence to the interpretation
        for key_result_type in results_ordered.values():
            key_result_type_sentences = []
            for idx, (sentence_key, results) in enumerate(key_result_type.items()):
                if len(results) == 0:
                    continue
                template = sentence_key['template'].replace("\n", "").strip()
                prefix = sentence_key.get('prefix', "").replace("\n", "").strip()
                substance_list_str = sentence_from_list(
                    list(map(lambda x: x.get_display_name(), results)),
                    results[0].result_type == ResultType.NEGATIVE,
                    False
                )
                if len(key_result_type_sentences) == 0 and prefix != "":
                    template = ' '.join([prefix, template])
                key_result_type_sentences.append(template.replace("%SUBS%", substance_list_str).strip())

            if len(key_result_type_sentences) == 0:
                continue

            # join sentence keys with the same key result typeß
            # we want results that are some type of positive to be a single sentence
            sentence = sentence_from_list(key_result_type_sentences, False, False) + '. '
            sentence = sentence[0].upper() + sentence[1:]
            self.interpretation += sentence

        # if the interp is empty, output a message saying no substances were detected
        if self.interpretation == '':
            self.interpretation = PROFILE['no_substances_template']

        # strip final interp
        self.interpretation = self.interpretation.strip()

    def __init__(self, predict_results: Dict[str, int], patient_results: dict, extra_ordered_codes: Set[str]) -> None:
        """
            Sets up data and generates an interpretation

            predict_results: a dictionary of targets and predictions from the ML model

            patient_results: a dictionary of codes and values

            extra_ordered_codes: a set of codes that were ordered but not included in results (batteries, packages, etc.)

            Internal properties:

            screen_results: the screen test results

            confirm_results: the confirmatory test results (-2 if not present)

            expected_results: the expected results (i.e. MOPIA...)
        """

        # initialize variables
        self.results = ResultCollection()
        self.results.clear()
        self.interpretation = ""

        screen_results = subset_dict(patient_results, SCREEN_CODES)
        confirm_results = subset_dict(patient_results, CONFIRM_CODES)
        expected_results = subset_dict(patient_results, EXPECTED_CODES_W_SECONDARY)

        expected_categories = subset_dict(patient_results, CAT_EXPECTED_CODES)

        ordered_codes = extra_ordered_codes.union(
            set(patient_results.keys()).difference(set(expected_results.keys())))

        # check to see if the invalid sample flag is true
        if 'Z_CAT_INVALID' in predict_results and predict_results['Z_CAT_INVALID'] == ResultType.POSITIVE:
            self.interpretation = PROFILE['invalid_template']
            return

        # Load specific substance predictions
        expected_codes = {k: v for k, v in expected_results.items() if v == ResultType.POSITIVE.value}
        for target_name, target_mapping in TARGET_MAPPINGS['targets'].items():

            if target_mapping['expected'] in expected_codes:
                # if we have a secondary expected code, and it's not included in
                # the results, set this to not expected
                secondary_expected = target_mapping.get('secondary_expected')
                if secondary_expected is not None:
                    if all(map(lambda x: x not in expected_codes, secondary_expected)):
                        expected = ResultType.NEGATIVE
                    else:
                        expected = ResultType.POSITIVE
                else:
                    expected = ResultType.POSITIVE
            else:
                expected = ResultType.NEGATIVE

            if target_name in predict_results:
                prediction = ResultType(predict_results[target_name])
            else:
                prediction = ResultType.MISSING

            self.results.add_result(
                SubstanceResult(
                    target_name = target_name,
                    is_expected = expected == ResultType.POSITIVE,
                    raw_uexpd = patient_results['UEXPD'] if 'UEXPD' in patient_results else "",
                    ordered_codes = ordered_codes,
                    screen = list(map(lambda x: CodeResult(x[0], x[1]), subset_dict(screen_results, target_mapping['screen']).items())),
                    confirm = list(map(lambda x: CodeResult(x[0], x[1]), subset_dict(confirm_results, target_mapping['confirm']).items())),
                    prediction = CodeResult(target_name, prediction)
                )
            )

        # Load category predictions
        for target_name, target_mapping in TARGET_MAPPINGS['category_targets'].items():

            if any(map(lambda x: x == ResultType.POSITIVE.value, subset_dict(expected_categories, target_mapping['expected']).values())):
                expected = ResultType.POSITIVE
                self.results.expecting_category(target_mapping['name'])
            else:
                expected = ResultType.NEGATIVE

            if target_name in predict_results:
                prediction = predict_results[target_name]
            else:
                prediction = ResultType.MISSING

            self.results.add_result(
                CategoryResult(
                    target_name = target_name,
                    is_expected = expected == ResultType.POSITIVE,
                    ordered_codes = ordered_codes,
                    prediction = CodeResult(target_name, prediction),
                )
            )

        # generate interpretation
        self.generate_interp()

    def __str__(self):
        return self.interpretation
