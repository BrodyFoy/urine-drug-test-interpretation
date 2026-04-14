from typing import List
from classifier.config import PROFILE
from classifier.processors import ResultProcessor
from classifier.result import FalsePositiveResult, ResultListState, ResultType, SubstanceResult
from classifier.result_collection import ResultCollection

class FalsePositiveProcessor(ResultProcessor):
    """
        Handles changing results to false positives if there are no other
        positive results in the screen
    """

    def process(results: ResultCollection):

        for screen, interp_results in results.results_by_screen.items():
            # continue is screen is negative
            if screen.result != ResultType.POSITIVE:
                continue

            substances: List[SubstanceResult] = list(filter(lambda x: isinstance(x, SubstanceResult), interp_results))

            # screen is only a false positive if
            # 1. All specific predictions have negative results
            # 2  No confirms are missing
            # 3. We have at least one confirm
            if len(substances) > 0:
                if all(map(lambda x: x.result_type == ResultType.NEGATIVE, substances)):
                    if any(map(lambda x: len(x.confirm) > 0, substances)):
                        if not any(map(lambda x: x.confirm_state == ResultListState.MISSING_ALL, substances)):
                            # remove all results with this screen
                            results.remove_results(interp_results)
                            results.add_result(FalsePositiveResult(
                                category = substances[0].get_category(), # assuming screens and categories are aligned
                                screen = screen,
                            ))
