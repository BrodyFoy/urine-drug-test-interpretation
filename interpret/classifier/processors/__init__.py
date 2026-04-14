from abc import abstractmethod

from classifier.result_collection import ResultCollection

class ResultProcessor:
    """
        Base class for processors, child classes will implement
        a process() method that takes a result collection, performs some
        operations on it (such as detecting negatives for all codes in a category)
        and updates the collection accordingly
    """

    @abstractmethod
    def process(results: ResultCollection):
        pass
