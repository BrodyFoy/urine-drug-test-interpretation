from typing import List, Set
from classifier.processors import ResultProcessor
from classifier.result import ResultListState, SubstanceResult
from classifier.result_collection import ResultCollection

class ScreenProcessor(ResultProcessor):
    """
        Handles marking substances with specific screens
        i.e. screens that only test for one substance
    """

    def process(results: ResultCollection):

        # get screens that reference multiple substances
        for screen, interp_results in results.results_by_screen.items():
            substances: List[SubstanceResult] = list(filter(lambda x: isinstance(x, SubstanceResult), interp_results))

            if (len(substances) == 1):
                substances[0].has_specific_screen = True

        # then remove the substances
        for screen, interp_results in results.results_by_screen.items():
            substances: List[SubstanceResult] = list(filter(lambda x: isinstance(x, SubstanceResult), interp_results))

            # remove substances that are missing all confirmatory results
            for substance in substances:
                # skip substance if it has a specific screen
                if substance.has_specific_screen:
                    continue

                if substance.confirm_state == ResultListState.MISSING_ALL:
                    # skip substance if it has a transfer name in UEXPD.
                    # in other words, if we mention Adderall, but only the screen for amphetamines
                    # is ordered, we assume there is evidence for Adderall
                    # similarly, if it's expected as well
                    if len(substance.get_expected_transfer_names()) > 0 or substance.is_expected:
                        continue

                    results.remove_results([substance])
