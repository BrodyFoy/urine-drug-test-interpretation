from typing import List
from ordered_set import OrderedSet
from classifier.config import TARGET_MAPPINGS
from classifier.processors import ResultProcessor
from classifier.processors.category_processor import CategoryProcessor
from classifier.result import CategoryResult, CodeResult, InterpretationResult, ResultType, SubstanceResult
from classifier.result_collection import ResultCollection


class SharedExpectedProcessor(ResultProcessor):
    """
        Handles a special case where two or more targets share an expected code.
        In this case, we want to remove any negative results from the interpretation
        so we don't mention an irrelevant (not actually expected) negative substance.
    """

    def process(results: ResultCollection):

        results_by_expected_category: dict[str, OrderedSet[InterpretationResult]] = {}
        substances: List[SubstanceResult] = list(filter(lambda x: isinstance(x, SubstanceResult), results.included_results))

        for substance in substances:
            if not substance.is_expected:
                continue

            target_mapping = TARGET_MAPPINGS['targets'][substance.code]

            expected_category = (target_mapping['expected'], substance.get_category())
            if expected_category not in results_by_expected_category:
                results_by_expected_category[expected_category] = OrderedSet()
            results_by_expected_category[expected_category].add(substance)

        for expected_category, expected_results in results_by_expected_category.items():
            if len(expected_results) > 1:
                # if we have more than one code assigned to this expected code
                # perform the algorithm
                # 1. check if any are non-negative (and non-missing)
                if any(filter(lambda x: x.result_type not in [ResultType.NEGATIVE, ResultType.MISSING], expected_results)):
                    # 2. remove other negative results
                    negative_results = list(filter(lambda x: x.result_type == ResultType.NEGATIVE, expected_results))
                    results.remove_results(negative_results)
                else:
                    # If they're all negative, include the category result for this expected code
                    category = list(filter(lambda x: isinstance(x, CategoryResult), results.results_by_category[expected_category[1]]))[0]
                    category.code_include_override = True
                    for result in expected_results:
                        result.is_expected = False
