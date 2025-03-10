from abc import ABC, abstractmethod

from frank_libs.dialogue_tree.nodes import (
    AbstractDialogueNode,
    AnswerVerificationResult,
    AbstractEndNode
)
from frank_libs.dialogue_tree.serde import JsonAnswerSerializer
from frank_libs.dialogue_tree.tree import DialogueTree


class AbstractInterpreter(ABC):
    def __init__(self, tree: DialogueTree):
        self._tree: DialogueTree = tree

        self._current_node: AbstractDialogueNode = self._tree.get_node(1)
        self._answers: JsonAnswerSerializer = JsonAnswerSerializer(self._tree)

    async def run(self):
        while True:
            question_text = self._current_node.get_question()

            await self._display_text(question_text)

            if not isinstance(self._current_node, AbstractEndNode):
                answer: str | None = await self._get_input()
            else:
                answer: str | None = None

            verification_result, answer_data = self._current_node.verify_answer(
                answer
            )

            if verification_result == AnswerVerificationResult.Ok:
                if answer_data is not None:
                    self._answers.add_answer(self._current_node.id, answer_data)
                else:
                    self._answers.add_answer(self._current_node.id, answer)

                next_node_id = self._current_node.get_next(answer)

                self._current_node = self._tree.get_node(next_node_id)
                if self._current_node is None:
                    await self._end_dialogue()
                    break
            else:
                msg = AnswerVerificationResult.to_message(
                    verification_result, answer_data
                )

                await self._display_text(f'{msg}, please try again...\n')

    @abstractmethod
    async def _display_text(self, text: str):
        pass

    @abstractmethod
    async def _get_input(self):
        pass

    @abstractmethod
    async def _end_dialogue(self):
        pass
