from typing import Dict, List, Set
from classifier.result import CodeResult, InterpretationResult, SubstanceResult

from ordered_set import OrderedSet

class ResultCollection:
    """
        Represents a collection of results, this could be
        categories or specific substances
    """

    # this will be included in the final interpretation
    included_results: OrderedSet[InterpretationResult] = OrderedSet()

    # this includes all results, regardless of final interpretation appearance
    results_by_category: Dict[str, List[InterpretationResult]] = {}

    results_by_screen: Dict[CodeResult, List[InterpretationResult]] = {}

    expected_categories: OrderedSet[str] = OrderedSet()

    def clear(self):
        self.included_results.clear()
        self.results_by_category.clear()
        self.results_by_screen.clear()
        self.expected_categories.clear()

    def expecting_category(self, category: str):
        """
            Adds a category to the expected categories set
        """
        self.expected_categories.add(category)

    def add_result(self, result: InterpretationResult):
        """
            Adds a new InterpretationResult to the collection
        """
        self.included_results.add(result)

        if isinstance(result, SubstanceResult):
            for screen in result.screen:
                if screen not in self.results_by_screen:
                    self.results_by_screen[screen] = []
                self.results_by_screen[screen].append(result)

        if result.get_category() not in self.results_by_category:
            self.results_by_category[result.get_category()] = []
        self.results_by_category[result.get_category()].append(result)

    def update_collection(self, results: List[InterpretationResult]):
        """
            Clears the collection and re-populates it with new results
        """
        self.clear()
        for result in results:
            self.add_result(result)

    def remove_results(self, to_remove: List[InterpretationResult]):
        """
            Removes results from the collection
        """
        self.included_results = OrderedSet(res for res in self.included_results if res not in to_remove)