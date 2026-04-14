from abc import abstractmethod
from enum import Enum
from functools import total_ordering
from typing import List, Set

from ordered_set import OrderedSet
from classifier.config import PROFILE, TARGET_MAPPINGS
from classifier.utility import FrozenDict

class ResultType(Enum):
    """
        Represents the possible values for a result
        Quantitative is just a placeholder so we can use confirm
        results in this type
    """
    INTERFERING = -3
    MISSING = -2
    NEGATIVE = 0
    POSITIVE = 1
    DISTANT = 2
    QUANTITATIVE = 3
    FALSE_POSITIVE = 4

class ResultListState(Enum):
    MISSING_ALL = 0,
    MISSING_SOME = 1,
    MISSING_NONE = 2

def compute_list_state(num_missing: int, list_length: int):
    """
        Computes the list state, this is an enum that determines
        whether all, some or no tests for a target are missing
    """
    list_state: ResultListState = ResultListState.MISSING_NONE
    if num_missing > 0:
        # we have some non-missing screens
        # are they all non missing?
        if num_missing == list_length:
            list_state = ResultListState.MISSING_ALL
        else:
            list_state = ResultListState.MISSING_SOME

    return list_state

class CodeResult:
    """
        Represents a test code or target
    """
    code: str = ""
    result: ResultType

    def __init__(self, code: str, result: int | float):
        if isinstance(result, float):
            self.result = ResultType.QUANTITATIVE
        else:
            try:
                self.result = ResultType(result)
            except ValueError:
                self.result = ResultType.QUANTITATIVE
        self.code = code

    def __hash__(self):
        return hash(self.code) ^ hash(self.result)

    def __eq__(self, other):
        if not isinstance(other, CodeResult):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.code == other.code and self.result == other.result

@total_ordering
class InterpretationResult:
    """
        Base class for results that will appear in the interpretation
    """

    code: str
    result_type: ResultType = ResultType.MISSING

    @abstractmethod
    def get_sentence_key(self) -> tuple[FrozenDict, str]:
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        pass

    @abstractmethod
    def get_category(self) -> str:
        pass

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        if not isinstance(other, InterpretationResult):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.code == other.code

    def __lt__(self, other):
        if not isinstance(other, InterpretationResult):
            return NotImplemented

        return self.code < other.code

class ExpectableResult(InterpretationResult):
    """
        Represents a result that can be "expected". In other words, this isn't something
        like a false positive - rather it's a category or specific substance
    """
    is_pharmaceutical: bool = False
    is_expected: bool = False
    code_include_override: bool = False
    code_exclude_override: bool = False

    def setup_code_overrides(self, ordered_codes: List[str]):
        """
            Determines whether this substance or category is included by
            the ordering of a battery/code or excluded. Requires "ordered_codes",
            a list of batteries or codes that need to be considered.
        """
        for code in ordered_codes:
            if code in PROFILE['code_overrides']:
                if self.get_category() in PROFILE['code_overrides'][code]['includes']:
                    self.code_include_override = True

        for code in ordered_codes:
            if code in PROFILE['code_overrides']:
                if self.get_category() in PROFILE['code_overrides'][code]['excludes'] and not self.code_include_override:
                    self.code_exclude_override = True

class FalsePositiveResult(InterpretationResult):
    """
        Used to mention specific screen codes when there is a false positive on one.
        We can't always claim the entire category is a false positive because some
        substances have specific screen codes
    """
    screen: CodeResult
    category: str

    def __init__(self, category: str, screen: CodeResult):
        self.code = screen.code
        self.category = category
        self.screen = screen
        self.result_type = ResultType.FALSE_POSITIVE

    def get_category(self):
        return self.category

    def get_display_name(self):
        # try to get name from screen_names
        screen_name = TARGET_MAPPINGS['screen_names'].get(self.code)

        if screen_name is not None:
            return screen_name.lower()
        else:
            return self.code.upper()

    def get_sentence_key(self):
        return FrozenDict(PROFILE['mappings']['false_positive']['false_positive']), 'false_positive'

class CategoryResult(ExpectableResult):
    """
        Represents the final result for a category.
        This is used in cases where an entire category of specific substances tests negative
        but we're expecting at least one positive/distant or in cases
        where there are no confirmatory results
    """

    prediction: CodeResult

    is_expected: bool

    def __init__(self, target_name, is_expected: bool, ordered_codes: List[str], prediction: CodeResult):
        self.code = target_name
        self.prediction = prediction
        self.is_expected = is_expected
        self.result_type = self.prediction.result

        self.setup_code_overrides(ordered_codes)

    def get_sentence_key(self):
        profile_mappings = PROFILE['mappings']
        if self.prediction.result == ResultType.POSITIVE:
            if self.is_expected:
                return FrozenDict(profile_mappings['positive']['expected']), 'positive'
            else:
                return FrozenDict(profile_mappings['positive']['unexpected']), 'positive'
        elif self.prediction.result == ResultType.NEGATIVE:
            return FrozenDict(profile_mappings['negative']['expected']), 'negative'
        return None, None

    def get_display_name(self):
        return TARGET_MAPPINGS['category_targets'][self.code]['name'].lower()

    def get_category(self):
        return self.get_display_name().capitalize()

class SubstanceResult(ExpectableResult):
    """
        Represents the final result for a substance
        given the confirmatory (if available) and screen info
        as well as the expected status.
    """
    display_name: str

    screen: List[CodeResult]
    confirm: List[CodeResult]
    prediction: CodeResult

    has_specific_screen: bool = False
    screen_state: ResultListState = ResultListState.MISSING_ALL
    confirm_state: ResultListState = ResultListState.MISSING_ALL

    raw_uexpd: str

    category: str

    def __init__(
                self,
                target_name: str,
                is_expected: bool,
                raw_uexpd: str,
                ordered_codes: List[str],
                screen: List[CodeResult],
                confirm: List[CodeResult],
                prediction: List[CodeResult]
            ):
        self.screen = screen
        self.confirm = confirm
        self.prediction = prediction
        self.code = target_name
        self.is_expected = is_expected
        self.raw_uexpd = raw_uexpd

        # get display name, is_pharmaceutical and other info from config
        target_mapping = TARGET_MAPPINGS['targets'][target_name]
        self.display_name = target_mapping['display_name']
        self.is_pharmaceutical = target_mapping['is_pharmaceutical']
        self.category = target_mapping['category']

        self.result_type = self.prediction.result

        num_missing_screens = len(list(filter(lambda x: x.result == ResultType.MISSING, self.screen)))
        num_missing_confirms = len(list(filter(lambda x: x.result == ResultType.MISSING, self.confirm)))
        self.screen_state = compute_list_state(num_missing_screens, len(self.screen))
        self.confirm_state = compute_list_state(num_missing_confirms, len(self.confirm))

        # If all confirms are missing, and all screens are missing, the result type is missing
        if len(self.confirm) == 0 or self.confirm_state == ResultListState.MISSING_ALL:
            if len(self.screen) == 0 or self.screen_state == ResultListState.MISSING_ALL:
                self.result_type = ResultType.MISSING

        # set up code include and exclude overrides
        self.setup_code_overrides(ordered_codes)

    def get_expected_transfer_names(self):
        target_mapping = TARGET_MAPPINGS['targets'][self.code]
        if 'transfer_names' in target_mapping and len(self.raw_uexpd) > 0:
            transfer_names = target_mapping['transfer_names']
            expected_transfers = []
            if len(transfer_names) > 0:
                for transfer_name in transfer_names:
                    if self.raw_uexpd.lower().find(transfer_name.lower()) != -1:
                        expected_transfers.append(transfer_name)

            return expected_transfers
        else:
            return []

    def get_display_name(self):
        name = self.display_name.lower()

        expected_transfers = self.get_expected_transfer_names()

        if len(expected_transfers) == 1 and expected_transfers[0] in PROFILE['transfer_name_non_brands']:
            name = expected_transfers[0]
        elif len(expected_transfers) > 0:
            name += f' ({", ".join(expected_transfers)})'

        return name

    def get_category(self):
        return self.category

    def is_screen_positive(self):
        return any(map(lambda x: x.result == ResultType.POSITIVE, self.screen))

    def get_sentence_key(self):
        """
            Gets the sentence that should wrap the list of substances
            this is a part of, we call it a key because it will be used
            as a key for a dictionary
        """

        key = None
        key_result_type = None
        profile_mappings = PROFILE['mappings']

        # first, check if any confirms or screens are XINSUB (Interfering)
        if any(map(lambda x: x.result == ResultType.INTERFERING, self.screen + self.confirm)):
            self.result_type = ResultType.INTERFERING
            # but only include them if they're expected:
            if self.is_expected:
                key_result_type = 'interfering'
                key = profile_mappings['interfering']['interfering']

        if self.result_type == ResultType.MISSING:
            key_result_type = 'negative'
            if self.is_expected and all(map(lambda x: x.result == ResultType.MISSING, self.confirm)):
                key = profile_mappings['negative']['expected_not_in_battery']

        if self.result_type == ResultType.POSITIVE:
            key_result_type = 'positive'
            if self.is_expected:
                if self.is_pharmaceutical:
                    key = profile_mappings['positive']['expected_pharmaceutical']
                else:
                    key = profile_mappings['positive']['expected']
            else:
                key = profile_mappings['positive']['unexpected']

        elif self.result_type == ResultType.NEGATIVE:
            key_result_type = 'negative'
            # it's a true negative (screen + prediction are false)
            if self.is_expected:
                if self.code_exclude_override:
                    key = profile_mappings['negative']['expected_not_in_battery']
                else:
                    key = profile_mappings['negative']['expected']

        elif self.result_type == ResultType.FALSE_POSITIVE:
            key_result_type = 'negative'
            key = PROFILE['mappings']['negative']['false_positive']

        elif self.result_type == ResultType.DISTANT:
            key_result_type = 'distant'
            if self.is_screen_positive():
                key = profile_mappings['distant']['positive']
            else:
                key = profile_mappings['distant']['negative']

        # override and remove when
        target_mapping = TARGET_MAPPINGS['targets'][self.code]
        if target_mapping.get('no_implicit_include', False):
            if not self.is_expected and not self.code_include_override:
                return None, None

        if key is None:
            return None, None

        return FrozenDict(key), key_result_type
