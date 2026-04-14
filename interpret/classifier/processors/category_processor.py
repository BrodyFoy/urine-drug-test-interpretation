from functools import reduce
from typing import List

from ordered_set import OrderedSet
from classifier.config import TARGET_MAPPINGS
from classifier.processors import ResultProcessor
from classifier.result import CategoryResult, ResultListState, ResultType, SubstanceResult
from classifier.result_collection import ResultCollection
from collections import Counter

class CategoryProcessor(ResultProcessor):
    """
        Handles the logic for deciding when to show category results
        like "no evidence for use of opioids"
    """
    def process(results: ResultCollection):

        for category, interp_results in results.results_by_category.items():
            # we only care about specific substances for this one
            substances: List[SubstanceResult] = list(filter(lambda x: isinstance(x, SubstanceResult), interp_results))
            category_results: List[CategoryResult] = list(filter(lambda x: isinstance(x, CategoryResult), interp_results))

            # show only the category when the following is true
            #   1. A code has overridden this category's inclusion (or one of it's substances)
            #   2. None of the specific substances in the category are expected
            #   3. No specific substances in the category are positive, distant or interfering
            case1 = len(category_results) > 0 and category_results[0].code_include_override
            case1 = case1 or any(filter(lambda x: x.code_include_override, substances))
            case1 = case1 and all(map(lambda x: not x.is_expected, substances))
            case1 = case1 and all(
                map(lambda x: x.result_type not in [ResultType.DISTANT, ResultType.POSITIVE, ResultType.INTERFERING], substances))

            # OR
            #  1. All confirms are missing
            #  2. There's at least one non-missing screen
            #  3. Category is not negative
            #  4. No transfer names are present
            #  5. No non-negative, specific screens
            #  6. None of the specific substances in the category are expected
            case2 = all(map(lambda x: x.confirm_state == ResultListState.MISSING_ALL or len(x.confirm) == 0, substances))
            case2 = case2 and any(map(lambda x: x.screen_state != ResultListState.MISSING_ALL, substances))
            case2 = case2 and any(map(lambda x: x.result_type == ResultType.POSITIVE, category_results))
            case2 = case2 and all(map(lambda x: len(x.get_expected_transfer_names()) == 0, substances))
            case2 = case2 and all(map(lambda x: not (x.has_specific_screen and x.result_type not in [ResultType.MISSING, ResultType.NEGATIVE]), substances))
            case2 = case2 and all(map(lambda x: not x.is_expected, substances))

            only_category_override = case1 or case2

            if only_category_override:
                # remove all specific results to avoid cluttering the final interpretation
                # with a million negative statements
                # but only do this if we have a category for this
                if category in map(lambda x: x.get_category(), category_results):
                    results.remove_results(substances)
                else:
                    # if we don't, force include it
                    for substance in substances:
                        if substance.code_include_override and substance.result_type != ResultType.MISSING:
                            substance.is_expected = True
                        results.included_results.add(substance)
                continue

            # if we're at this point, just remove the category result since we
            # have some sort of specifics we want to mention
            results.remove_results(category_results)
