import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, cast

from frank_libs.vos.vos import SlackUserVo


class AnswerVerificationResult(Enum):
    Ok = 1,
    ExpectedNumber = 2,
    OutOfRange = 3
    NotEnoughArguments = 4
    TooManuArguments = 5
    SlackUserNotFound = 6

    # todo instantiate, add arguments
    @staticmethod
    def to_message(value) -> str | None:
        if value == AnswerVerificationResult.Ok:
            return None
        elif value == AnswerVerificationResult.ExpectedNumber:
            return 'Expecting number as an answer'
        elif value == AnswerVerificationResult.OutOfRange:
            return 'Your answer is out of range'
        elif value == AnswerVerificationResult.NotEnoughArguments:
            return "You haven't supplied enough arguments"
        elif value == AnswerVerificationResult.TooManuArguments:
            return "You have supplied too many arguments"
        elif value == AnswerVerificationResult.SlackUserNotFound:
            return "Slack user not found"


class AbstractDialogueNode(ABC):
    def __init__(self, id_: int, text: str):
        self._id: int = id_
        self._text = text

    @property
    def id(self) -> int:
        return self._id

    @property
    def text(self):
        return self._text

    @staticmethod
    @abstractmethod
    def from_dict(node_id: int, node_def: dict) -> object:
        pass

    @abstractmethod
    def get_question(self) -> str | None:
        pass

    @abstractmethod
    def get_next(self, answer: str) -> int:
        pass

    @abstractmethod
    def verify_answer(self, answer: str | None) -> AnswerVerificationResult:
        pass


class AbstractOneAnswerNode(AbstractDialogueNode, ABC):
    def __init__(self, id_: int, text: str, next_node: int | None):
        super().__init__(id_, text)

        self._next_node: int | None = next_node

    # Used for validation
    @property
    def next_node(self) -> int | None:
        return self._next_node

    def get_question(self) -> str | None:
        return f'{self._text}'

    def get_next(self, answer: str) -> int | None:
        return self._next_node


class BaseInjectableNode:

    def __init__(self):
        self._injected_data: Any | None = None

    def inject_data(self, data: Any):
        self._injected_data = data


class ChoiceDialogueNode(AbstractDialogueNode):

    def __init__(
            self, id_: int, text: str, choices: dict[int, str]
    ):
        super().__init__(id_, text)

        self._choices: dict[int, str] = choices

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']

        choices: dict[int, str] = {}
        for choice_id, choice_text in node_def['choices'].items():
            choices[int(choice_id)] = choice_text

        return ChoiceDialogueNode(node_id, node_text, choices)

    def get_question(self) -> str | None:
        s = f"{self._text}\n"

        for i, (node_id, choice_text) in enumerate(self._choices.items()):
            abbrev = i + 1
            s += f'   {abbrev}) {choice_text}\n'

        return s[:-1]

    def get_next(self, answer: str) -> int:
        index = int(answer) - 1
        return list(self._choices.keys())[index]

    def verify_answer(self, answer: str) -> AnswerVerificationResult:
        try:
            i = int(answer) - 1
            if i < len(self._choices.keys()):
                return AnswerVerificationResult.Ok
            else:
                return AnswerVerificationResult.OutOfRange
        except ValueError:
            return AnswerVerificationResult.ExpectedNumber

    def get_choices(self):
        return self._choices

    def __str__(self):
        choices = ''
        for target_node_id, choice_text in self._choices.items():
            choices += (
                f'        target_node_id={target_node_id}\n'
                f'        text={choice_text}\n'
            )

        return f'ChoiceNode: \n    choices:\n{choices}'


class QuantifiableDialogueNode(AbstractDialogueNode):
    class QuantifiableChoice:
        def __init__(
                self,
                target_id: int | None,
                min_: float | None,
                max_: float | None
        ):
            self.target_id = target_id
            self.min = min_
            self.max = max_

        def __str__(self):
            return (
                f"[target_ID={self.target_id}, min={self.min}, max={self.max}]"
            )

    def __init__(
            self,
            id_: int,
            text: str,
            min_value: float | None,
            max_value: float | None,
            choices: dict[int, QuantifiableChoice]
    ):
        super().__init__(id_, text)

        self._min_value: float | None = min_value
        self._max_value: float | None = max_value
        self._choices: dict[
            int, QuantifiableDialogueNode.QuantifiableChoice
        ] = choices

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']
        enum_min_max = False
        try:
            min_value = float(node_def['min_value'])
            max_value = float(node_def['max_value'])
        except KeyError:
            min_value = 0
            max_value = 0
            enum_min_max = True

        choices: dict[int, QuantifiableDialogueNode.QuantifiableChoice] = {}
        _min_value = 0
        _max_value = 0
        for choice in node_def['choices']:
            target_id = int(choice['target_id'])
            min_ = float(choice['min'])
            max_ = float(choice['max'])
            if min_ < _min_value:
                _min_value = min_
            if max_ > _max_value:
                _max_value = max_
            choices[target_id] = (
                QuantifiableDialogueNode
                .QuantifiableChoice(target_id, min_, max_)
            )

        if enum_min_max:
            min_value = _min_value
            max_value = _max_value

        return QuantifiableDialogueNode(
            node_id, node_text, min_value, max_value, choices
        )

    def get_question(self) -> str | None:
        return f'{self._text} [{self._min_value}..{self._max_value}]'

    def get_next(self, answer: str) -> int:
        n = float(answer)
        for target_id, choice in self._choices.items():
            if choice.min <= n <= choice.max:
                return choice.target_id

        # This is a failsafe, we should check the `choices` structure during
        # tree creation time, so there are no holes and this may never happen
        return -1

    def verify_answer(self, answer: str) -> AnswerVerificationResult:
        try:
            n = float(answer)
            if self._min_value <= n <= self._max_value:
                return AnswerVerificationResult.Ok
            else:
                return AnswerVerificationResult.OutOfRange
        except ValueError:
            return AnswerVerificationResult.ExpectedNumber

    def get_choices(self):
        return self._choices

    def __str__(self):
        choices = ''
        for id_, q_choice in self._choices.items():
            choices += (
                f'        target_node_id={id_}\n'
                f'        min={q_choice.min}...{q_choice.max}\n'
                f'        text={self._text}\n'
            )

        return f'QuantifiableNode:\n    choices:    \n{choices}'


class IntervalDialogueNode(AbstractDialogueNode):
    def __init__(
            self,
            id_: int,
            text: str,
            choices: list[(float, int)]
    ):
        super().__init__(id_, text)

        self._choices: list = choices
        self._min_value, self._max_value = self._get_boundaries(choices)

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']

        choices: list = []
        for choice in node_def['choices']:
            if isinstance(choice, list):
                num = float(choice[0])
                target_id = int(choice[1])
                choices.append((num, target_id))
            else:
                num = float(choice)
                choices.append((num, -1))

        return IntervalDialogueNode(node_id, node_text, choices)

    def get_question(self) -> str | None:
        return f'{self._text} [{self._min_value}..{self._max_value}]'

    def get_next(self, answer: str) -> int:
        n = float(answer)
        for i, choice in enumerate(self._choices[:-1]):
            next_ = self._choices[i + 1]
            if isinstance(next_, tuple):
                val = float(next_[0])
            else:
                val = float(next_)

            if n <= val:
                return choice[1]

    def verify_answer(self, answer: str) -> AnswerVerificationResult:
        try:
            n = float(answer)
            if self._min_value <= n <= self._max_value:
                return AnswerVerificationResult.Ok
            else:
                return AnswerVerificationResult.OutOfRange
        except ValueError:
            return AnswerVerificationResult.ExpectedNumber

    @staticmethod
    def _get_boundaries(choices: list) -> tuple[float | None, float | None]:
        min_ = None
        max_ = None
        for value, target_id in choices:
            value = float(value)
            if min_ is None or value < min_:
                min_ = value
            if max_ is None or value > max_:
                max_ = value

        if min_ is None:
            min_ = 0
        if max_ is None:
            max_ = 0

        return min_, max_

    def get_choices(self):
        return self._choices

    def __str__(self):
        choices = ''
        for i, choice_tuple in enumerate(self._choices):
            choices += (
                f'        target_node_id={choice_tuple[1]}\n'
                f'        interval={choice_tuple[0]}...\n'
                f'        text={self._text}\n'
            )

        return f'IntervalNode: \n    choices:\n{choices}'


class GenericQuestionDialogueNode(AbstractOneAnswerNode):
    def __init__(self, id_: int, text: str, next_node: int | None):
        super().__init__(id_, text, next_node)

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']
        try:
            next_node: int | None = int(node_def['next_node'])
        except TypeError:
            next_node: int | None = None

        return GenericQuestionDialogueNode(node_id, node_text, next_node)

    def verify_answer(self, answer: str) -> AnswerVerificationResult:
        return AnswerVerificationResult.Ok

    def __str__(self):
        return (
            f'GenericNode: \n    choices:\n    '
            f'    target_node_id={self._next_node}\n'
            f'        text={self._text}\n'
        )


class SlackUsersChooseDialogueNode(AbstractOneAnswerNode, BaseInjectableNode):

    def __init__(self, id_: int, text: str, next_node: int | None):
        super().__init__(id_, text, next_node)

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']
        try:
            next_node: int | None = int(node_def['next_node'])
        except TypeError:
            next_node: int | None = None

        return SlackUsersChooseDialogueNode(node_id, node_text, next_node)

    def verify_answer(self, answer: str | None) -> AnswerVerificationResult:
        data = cast(dict[int, SlackUserVo], self._injected_data)
        for slack_user in data.values():
            if answer == slack_user.profile__display_name:
                return AnswerVerificationResult.Ok

        return AnswerVerificationResult.SlackUserNotFound

    def __str__(self):
        return (
            f'SlackUsersNode: \n    choices:\n    '
            f'    target_node_id={self._next_node}\n'
            f'        text={self._text}\n'
        )


class EndDialogueNode(AbstractDialogueNode):
    def __init__(self, id_: int, text: str):
        super().__init__(id_, text)

    @staticmethod
    def from_dict(node_id: int, node_def: dict) -> AbstractDialogueNode:
        node_text: str = node_def['text']

        return EndDialogueNode(node_id, node_text)

    def get_question(self) -> str | None:
        return f'{self._text}'

    def get_next(self, answer: str) -> int:
        return -1

    def verify_answer(self, answer: str) -> AnswerVerificationResult:
        return AnswerVerificationResult.Ok

    def __str__(self):
        return f'EndNode: \n    text: {self._text}\n'


# todo do we really need this to be abstract with subclasses -> No. ?

class AbstractAnswer(ABC):
    def __init__(self, id_: int):
        self._id: int = id_
        self._answer: str | int | float | None = None
        self._time: float = time.time()

    @property
    def answer(self) -> str | int | float | None:
        return self._answer

    @property
    def time(self):
        return self._time

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "answer": self._answer,
            "time": self._time
        }

    def __str__(self) -> str:
        return f'Answer: id={self._id}, answer={self._answer}'


class ChoiceAnswer(AbstractAnswer):
    def __init__(self, id_: int, answer: int):
        super().__init__(id_)
        self._answer = answer


class QuantifiableAnswer(AbstractAnswer):
    def __init__(self, id_: int, answer: float):
        super().__init__(id_)
        self._answer = answer


class IntervalAnswer(AbstractAnswer):
    def __init__(self, id_: int, answer: float):
        super().__init__(id_)
        self._answer = answer


class GenericAnswer(AbstractAnswer):
    def __init__(self, id_: int, answer: str):
        super().__init__(id_)
        self._answer = answer


class SlackUsersAnswer(AbstractAnswer):
    def __init__(self, id_: int, answer: str):
        super().__init__(id_)
        self._answer = answer


class EndAnswer(AbstractAnswer):
    def __init__(self, id_: int):
        super().__init__(id_)
