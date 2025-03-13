import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import cast

from frank_libs.dialogue_tree.nodes import (
    AbstractDialogueNode,
    ChoiceDialogueNode,
    QuantifiableDialogueNode,
    GenericQuestionDialogueNode,
    SlackUsersChooseDialogueNode,
    IntervalDialogueNode,
    EndDialogueNode,
    AbstractAnswer,
    GenericAnswer,
    NotificationNode,
)
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

        cls_map: dict[str, type[AbstractDialogueNode]] = {
            JsonNode.Choice.value: ChoiceDialogueNode,
            JsonNode.Quantifiable.value: QuantifiableDialogueNode,
            JsonNode.GenericQuestion.value: GenericQuestionDialogueNode,
            JsonNode.SlackUsers.value: SlackUsersChooseDialogueNode,
            JsonNode.Interval.value: IntervalDialogueNode,
            JsonNode.Notification.value: NotificationNode,
            JsonNode.End.value: EndDialogueNode,
        }
        cls = cls_map.get(node_type)
        if cls:
            return cast(AbstractDialogueNode, cls.from_dict(node_id, node_def))
        else:
            return None

    @staticmethod
    def answer_from_node(
            node: AbstractDialogueNode,
            answer: str | float | int | None
    ) -> AbstractAnswer | None:
        return GenericAnswer(node.id, answer)


class AbstractJsonDeserializer(ABC):
    def __init__(self):
        self._tree: DialogueTree | None = None

    @property
    def tree(self) -> DialogueTree | None:
        return self._tree

    @abstractmethod
    def deserialize(self):
        pass

    def _deserialize(self, id_: int, nodes: dict[int | str, dict],
                     urgent: bool):
        self._tree = DialogueTree(id_, urgent)
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
            self._deserialize(o['id'], nodes, o['urgent'])


class DictJsonTreeDeserializer(AbstractJsonDeserializer):
    def __init__(
            self, id_: int, tree_dict: dict[int | str, dict], urgent: bool
    ):
        super().__init__()
        self._tree_dict = tree_dict
        self._urgent = urgent
        self._id = id_

    def deserialize(self):
        self._deserialize(self._id, self._tree_dict, self._urgent)


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

    def deserialize(self):
        answers = []
        for a in self._answers:
            answers.append(a.to_dict())

        self._data_dict = {
            "time_start": self._answers[0].time if self._answers else -1,
            "time_end": self._answers[-1].time if self._answers else -1,
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
