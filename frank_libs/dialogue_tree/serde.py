import json
from abc import ABC, abstractmethod
from enum import Enum

from frank_libs.dialogue_tree.nodes import AbstractDialogueNode, \
    ChoiceDialogueNode, QuantifiableDialogueNode, GenericQuestionDialogueNode, \
    SlackUsersChooseDialogueNode, IntervalDialogueNode, EndDialogueNode, \
    AbstractAnswer, ChoiceAnswer, QuantifiableAnswer, GenericAnswer, \
    IntervalAnswer, SlackUsersAnswer, EndAnswer, NotificationNode, \
    NotificationAnswer
from frank_libs.dialogue_tree.tree import DialogueTree


class JsonNode(Enum):
    Choice = "choice"
    Quantifiable = "quantifiable"
    GenericQuestion = "question"
    Interval = "interval"
    SlackUsers = "slack_users"
    Notification = "notification"
    End = "end"

    @staticmethod
    def node_from_def(
            node_id: int,
            node_def: dict
    ) -> AbstractDialogueNode | None:
        node_id = int(node_id)
        node_type = node_def['type']

        if node_type == JsonNode.Choice.value:
            return ChoiceDialogueNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.Quantifiable.value:
            return QuantifiableDialogueNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.GenericQuestion.value:
            return GenericQuestionDialogueNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.SlackUsers.value:
            return SlackUsersChooseDialogueNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.Interval.value:
            return IntervalDialogueNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.Notification.value:
            return NotificationNode.from_dict(node_id, node_def)
        elif node_type == JsonNode.End.value:
            return EndDialogueNode.from_dict(node_id, node_def)
        else:
            return None

    @staticmethod
    def answer_from_node(
            node: AbstractDialogueNode,
            answer: str | float | int | None
    ) -> AbstractAnswer | None:
        if isinstance(node, ChoiceDialogueNode):
            return ChoiceAnswer(node.id, answer)
        elif isinstance(node, QuantifiableDialogueNode):
            return QuantifiableAnswer(node.id, answer)
        elif isinstance(node, GenericQuestionDialogueNode):
            return GenericAnswer(node.id, answer)
        elif isinstance(node, IntervalDialogueNode):
            return IntervalAnswer(node.id, answer)
        elif isinstance(node, SlackUsersChooseDialogueNode):
            return SlackUsersAnswer(node.id, answer)
        elif isinstance(node, NotificationNode):
            return NotificationAnswer(node.id, answer)
        elif isinstance(node, EndDialogueNode):
            return EndAnswer(node.id)
        else:
            return None


class AbstractJsonDeserializer(ABC):
    def __init__(self):
        self._tree: DialogueTree = DialogueTree()

    @property
    def tree(self) -> DialogueTree | None:
        return self._tree

    @abstractmethod
    def deserialize(self):
        pass

    def _deserialize(self, nodes: dict[int | str, dict]):
        for node_id, node_def in nodes.items():
            node_id = int(node_id)
            node = JsonNode.node_from_def(node_id, node_def)
            self._tree.add_node(node_id, node)



class FileJsonTreeDeserializer(AbstractJsonDeserializer):
    def __init__(self, json_path: str):
        super().__init__()
        self._path: str = json_path

    def deserialize(self):
        with open(self._path) as f:
            o: dict = json.loads(f.read())
            nodes: dict = o['nodes']
            self._deserialize(nodes)


class DictJsonTreeDeserializer(AbstractJsonDeserializer):
    def __init__(self, tree_dict: dict[int | str, dict]):
        super().__init__()
        self._tree_dict = tree_dict

    def deserialize(self):
        self._deserialize(self._tree_dict)


# todo not serializer, rather container with to_dict
class JsonAnswerSerializer:
    def __init__(self, dialogue_tree: DialogueTree):
        self._dialogue_tree = dialogue_tree
        self._answers: list[AbstractAnswer] = []
        self._data: str | None = None
        self._data_dict: dict | None = None

    @property
    def data(self) -> dict | None:
        return self._data

    @property
    def data_dict(self) -> dict | None:
        return self._data_dict

    def add_answer(self, node_id: int, answer: str | float | int):
        question_node = self._dialogue_tree.get_node(node_id)
        self._answers.append(JsonNode.answer_from_node(question_node, answer))

    def serialize_as_dict(self):
        answers = []
        for a in self._answers:
            answers.append(a.to_dict())

        self._data_dict = {
            "time_start": self._answers[0].time,
            "time_end": self._answers[-1].time,
            "answers": answers
        }

    def serialize(self):
        answers = []
        for a in self._answers:
            answers.append(a.to_dict())

        self._data = json.dumps({
            "time_start": self._answers[0].time,
            "time_end": self._answers[-1].time,
            "answers": answers
        })
