from abc import ABC
from collections import deque
from enum import Enum
from typing import Any, cast

from frank_libs.dialogue_tree.nodes import AbstractDialogueNode, \
    SlackUsersChooseDialogueNode, BaseInjectableNode, ChoiceDialogueNode, \
    QuantifiableDialogueNode, GenericQuestionDialogueNode, IntervalDialogueNode, \
    EndDialogueNode, AbstractOneAnswerNode


class DataInjectionRequest(Enum):
    SlackUsers = 1


class DialogueTree:
    def __init__(self):
        self._tree: dict[int, AbstractDialogueNode] = {}
        self._validator = TreeDialogueValidator(self)
        self._present_node_types: set[type[AbstractDialogueNode]] = set()

    @property
    def requested_data_injections(self) -> list[DataInjectionRequest]:
        ret = []
        if SlackUsersChooseDialogueNode in self._present_node_types:
            ret.append(DataInjectionRequest.SlackUsers)

        return ret

    def add_node(
            self,
            id_: int,
            node: AbstractDialogueNode,
    ):
        self._tree[id_] = node
        self._present_node_types.add(node.__class__)

    def get_node(self, node_id: int) -> AbstractDialogueNode | None:
        return self._tree.get(node_id)

    def get_nodes(self) -> dict[int, AbstractDialogueNode]:
        return self._tree

    def inject_data(
            self,
            node_type: type[AbstractDialogueNode, BaseInjectableNode],
            data: Any
    ):
        for node in self._tree.values():
            if isinstance(node, node_type):
                injectable_node = cast(BaseInjectableNode, node)
                injectable_node.inject_data(data)

    def __str__(self):
        s = ""
        for id_, node in self._tree.items():
            s += f"id: {id_}, node: {node}\n"

        return s


class AbstractValidationReport(ABC):
    def __init__(self, node_id: int):
        self._node_id = node_id
        self._message: str | None = None

    @property
    def node_id(self):
        return self._node_id

    @property
    def message(self):
        return self._message


class ValidationReportSummary:
    def __init__(self):
        self._reports: dict[int, list[AbstractValidationReport]] = {}

    def add_reports(self, reports: list[AbstractValidationReport]):
        for report in reports:
            if not self._reports.get(report.node_id):
                self._reports[report.node_id] = []
            self._reports[report.node_id].append(report)

    @property
    def reports(self):
        return self._reports


"""
-==============================================================================-
|                        =<| Validation Reports |>=                            | 
-==============================================================================-
"""


class InvalidChoiceNoAnswerReport(AbstractValidationReport):
    """
    ChoiceDialogueNode: User hasn't filled the choice(s) text.
    """

    def __init__(self, node_id: int, invalid_choices_ids: list[int]):
        super().__init__(node_id)
        self._invalid_choices_ids = invalid_choices_ids

        s = _helper_mk_str_list(invalid_choices_ids)

        self._message = (
            f"User hasn't filled the choice(s) text in node with id={node_id}, "
            f"and choice(s)_id(s)={s}"
        )

    def __str__(self):
        return (
            f"InvalidChoiceNoAnswerReport: node_id={self._node_id} "
            f"invalid_choice(s)_id(s): {self._invalid_choices_ids}"
        )


class InvalidQuantifiableChoiceReport(AbstractValidationReport):
    def __init__(self, node_id: int,
                 invalid_choices: list[tuple[int, float, float]]):
        super().__init__(node_id)
        self._invalid_choices = invalid_choices

        self._message = (
            "User has set wrong intervals, there can not be any gaps in "
            f"intervals: {self._mk_str_from_invalid_choices()}"
        )

    def __str__(self):
        return (
            f"InvalidQuantifiableChoiceReport: node_id={self._node_id}, "
            f"invalid_targets={self._mk_str_from_invalid_choices()}"
        )

    def _mk_str_from_invalid_choices(self):
        l = len(self._invalid_choices) - 1
        s = '('
        for i, (target_id, min_, max_) in enumerate(self._invalid_choices):
            if i < l:
                s += f'[target_id={target_id}, min={min_}, max={max_}], '
            else:
                s += f'[target_id={target_id}, min={min_}, max={max_}])'
        return s


class InvalidIntervalSameNumberReport(AbstractValidationReport):
    def __init__(self, node_id: int, target_id: int, n: float):
        super().__init__(node_id)
        self._target_id = target_id
        self._n = n

        self._message = (
            f"User has set same numbers in the interval, node_id={node_id}, "
            f"target_id={target_id}, number={n}"
        )

    def __str__(self):
        return (
            f"InvalidIntervalSameNumberReport: node_id={self._node_id}, "
            f"target_id={self._target_id}, number={self._n}"
        )


class NoEdgesOnNodeReport(AbstractValidationReport):
    def __init__(self, node_id: int):
        super().__init__(node_id)

        self._message = F"Node with node_id={node_id} has no answers."

    def __str__(self):
        return (
            f"NoEdgesOnNodeReport: node_id={self._node_id}"
        )


class NodeNotTraversableToNodeId1(AbstractValidationReport):
    def __init__(self, node_id: int):
        super().__init__(node_id)

        self._message = (
            f"Node with node_id={self.node_id} not connected to the rest of the"
            " graph."
        )

    def __str__(self):
        return (
            f'NodeNotConnectedToNodeId1: node_id={self._node_id}'
        )


"""
Below are reports indicating that someone is messing with our API.
"""


class BaseMalformedDataReport(AbstractValidationReport):
    """
    Base class for reports which cannot be achieved via using Dialogue Creator.
    """
    pass


class InvalidSubmitReport(BaseMalformedDataReport):
    """
    This cannot happen by normal usage of the Dialogue Creator. It basically
    means that someone is trying to mess with us, and this has to be clearly
    visible in Grafana.
    """

    def __init__(self, node_id):
        super().__init__(node_id)
        self._message = (
            f'We encountered node_id={node_id} which has no corresponding node'
            f'in the graph. This cannot happen by normal usage of the Dialogue'
            f'Creator and should be further investigated.'
        )

    def __str__(self):
        return (
            f"InvalidSubmitReport: node_id={self.node_id}"
        )


class InvalidNodeNameReport(BaseMalformedDataReport):
    """
    This shouldn't happen while user is using Dialogue Creator, i.e. someone is
    trying to mess with our API, node_text is either empty string or None after
    deserialization.
    """

    def __init__(self, node_id: int, node_text: str | None):
        super().__init__(node_id)

        self._node_text = node_text

        self._message = (
            f"Node with id={node_id} has not filled the question text, "
            f"text='{node_text}"
        )

    def __str__(self):
        return (
            f"InvalidNodeNameReport: node_id={self._node_id},"
            f" node_name='{self._node_text}'"
        )


class InvalidTargetNodeIdReport(BaseMalformedDataReport):
    """
    This shouldn't happen while user is using Dialogue Creator, i.e. someone is
    trying to mess with our API.
    """

    def __init__(self, node_id: int, target_node_ids: list[int]):
        super().__init__(node_id)

        self._target_node_ids = target_node_ids
        s = _helper_mk_str_list(target_node_ids)

        self._message = (
            f"Node with id={node_id} has invalid choice target node_i(d)s: "
            f"{s}"
        )

    def __str__(self):
        return (
            f"InvalidTargetNodeIdReport: node_id={self._node_id}, "
            f"target_node_id(s)={_helper_mk_str_list(self._target_node_ids)}"
        )


class InvalidIntervalSameTargetIdReport(BaseMalformedDataReport):
    """
    This shouldn't happen while user is using Dialogue Creator, i.e. someone is
    trying to mess with our API.
    """

    def __init__(self, node_id: int, target_id: int):
        super().__init__(node_id)

        self._target_id = target_id

        self._message = (
            f"Node with id={node_id} has 2 answers for same target node "
            f"target_id={target_id}"
        )

    def __str__(self):
        return (
            f"SameTargetIdReport: node_id={self._node_id}, "
            f"target_node_id={self._target_id}"
        )


class InvalidQuantifiableNoneChoiceReport(BaseMalformedDataReport):
    """
    This shouldn't happen while user is using Dialogue Creator, i.e. someone is
    trying to mess with our API.
    """

    def __init__(self, node_id: int):
        super().__init__(node_id)

        self._message = (
            f"QuantifiableNode with id={node_id} has None in the interval."
        )

    def __str__(self):
        return f"InvalidQuantifiableNoneChoiceReport: node_id={self._node_id}"


def _helper_mk_str_list(lst: list[int | float | str]) -> str:
    s = '('
    l = len(lst) - 1
    for i, item in enumerate(lst):
        if i < l:
            s += f'{item}, '
        else:
            s += f'{item})'

    return s


"""
-==============================================================================-
|                      =<| Tree Dialogue Validator |>=                         | 
-==============================================================================-
"""


class TreeDialogueValidator:
    def __init__(self, tree: DialogueTree):
        self._tree = tree

        self._compact_graph_data = self._mk_graph_data()
        self._report_summary = ValidationReportSummary()

    @property
    def report_summary(self):
        return self._report_summary

    def validate(self) -> None:
        """
        Validate all nodes. We check if edges (answers) are properly filled,
        if all nodes are connected to the graph, and if nodes which are not End
        Node have at least one edge. We also check possible errors that
        shouldn't happen when user is using Dialogue Creator, i.e. if someone is
        trying to send 'trash' data to the API. There is no possibility that by
        doing this he could break the server, because FastApi just returns 500,
        but we want to detect this behaviour and possibly remove such user
        from our service.
        """
        nodes = self._tree.get_nodes()

        for id_, node in nodes.items():
            if isinstance(node, ChoiceDialogueNode):
                reports = self._validate_choice_node(node)
            elif isinstance(node, QuantifiableDialogueNode):
                reports = self._validate_quantifiable_node(node)
            elif isinstance(
                    node,
                    (
                            GenericQuestionDialogueNode,
                            SlackUsersChooseDialogueNode
                    )
            ):
                reports = self._validate_one_answer_node(node)
            elif isinstance(node, IntervalDialogueNode):
                reports = self._validate_interval_node(node)
            elif isinstance(node, EndDialogueNode):
                reports = self._validate_end_node(node)
            else:
                # This really cannot happen (tree wouldn't be serialized in this
                # case), it's here just to calm down IDE's checks
                reports = None

            # Check if we can traverse to node with id 1
            if not self._check_path_exists(node.id):
                if not reports:
                    reports = [NodeNotTraversableToNodeId1(node.id)]
                else:
                    reports.append(NodeNotTraversableToNodeId1(node.id))

            if reports is not None:
                self._report_summary.add_reports(reports)

    """
    -==========================================================================-
    |                         =<| Node Validation |>=                          | 
    -==========================================================================-
    """

    def _validate_choice_node(
            self,
            node: ChoiceDialogueNode
    ) -> list[AbstractValidationReport] | None:
        # Validate node name
        reports = []
        report = TreeDialogueValidator._validate_node_name(node)
        if report:
            reports.append(report)

        # Validate choices, choice has to have proper text i.e. not empty string
        choices = node.get_choices()
        invalid_choices = []
        invalid_target_ids = []
        target_ids = []
        for target_id, choice_text in choices.items():
            target_ids.append(target_id)

            if choice_text == "":
                invalid_choices.append(target_id)

            if not self._validate_target_id(target_id):
                invalid_target_ids.append(target_id)

        if len(invalid_choices) != 0:
            reports.append(
                InvalidChoiceNoAnswerReport(node.id, invalid_choices)
            )

        if len(invalid_target_ids) > 0:
            reports.append(
                InvalidTargetNodeIdReport(node.id, invalid_target_ids)
            )
        # Check if there are any answers at this node
        if len(choices) == 0:
            reports.append(NoEdgesOnNodeReport(node.id))

        if len(reports) == 0:
            return None
        else:
            return reports

    def _validate_quantifiable_node(
            self,
            node: QuantifiableDialogueNode
    ) -> list[AbstractValidationReport] | None:
        # Validate node name
        reports = []
        report = TreeDialogueValidator._validate_node_name(node)
        if report:
            reports.append(report)

        choices = node.get_choices()

        # Validate intervals, there has to be no gap
        choices_list = []
        for target_node_id, choice in choices.items():
            choices_list.append((target_node_id, choice))

        sorted_choices = sorted(
            choices_list,
            key=lambda choice_: choice_[1].min
        )

        last_min: float | None = None
        last_max: float | None = None
        last_target_id: int | None = None
        invalid_target_ids = []
        target_ids = []
        invalid_choices = []
        for target_id, choice in sorted_choices:
            target_ids.append(target_id)
            target_ids.append(target_id)
            if choice.min is None or choice.max is None:
                InvalidQuantifiableNoneChoiceReport(node.id)
                break

            # Also validate target IDs in one pass, nodes with target_id must
            # exist
            if not self._validate_target_id(target_id):
                invalid_target_ids.append(target_id)

            if choice.min == choice.max:
                invalid_choices.append((target_id, choice.min, choice.max))

            if last_min is not None and last_max is not None:
                if choice.min != last_max:
                    invalid_choices.append((last_target_id, last_min, last_max))

            last_min = choice.min
            last_max = choice.max
            last_target_id = target_id

        if invalid_choices:
            reports.append(
                InvalidQuantifiableChoiceReport(node.id, invalid_choices)
            )

        if len(invalid_target_ids) > 0:
            reports.append(
                InvalidTargetNodeIdReport(node.id, invalid_target_ids)
            )

        # Check if there are any answers at this node
        if len(choices) == 0:
            reports.append(NoEdgesOnNodeReport(node.id))

        if len(reports) > 0:
            return reports
        else:
            return None

    def _validate_one_answer_node(
            self,
            node: AbstractOneAnswerNode
    ) -> list[AbstractValidationReport] | None:
        # Validate node name
        reports = []
        report = TreeDialogueValidator._validate_node_name(node)
        if report:
            reports.append(report)

        # OneAnswerNode Question must point to another node
        if node.next_node is None:
            # Check if there are any answers at this node
            reports.append(NoEdgesOnNodeReport(node.id))
        else:
            if not self._validate_target_id(node.next_node):
                reports.append(
                    InvalidTargetNodeIdReport(node.id, [node.next_node])
                )

        if len(reports) > 0:
            return reports
        else:
            return None

    def _validate_interval_node(
            self,
            node: IntervalDialogueNode
    ) -> list[AbstractValidationReport] | None:
        # Validate node name
        reports = []
        report = TreeDialogueValidator._validate_node_name(node)
        if report:
            reports.append(report)

        # In Interval Node, there cannot be same numbers and every number has
        # to be set (can not be None), also target_id must point to the
        # existing node. Validate target_ids as well, if they are None, it's
        # indication that something funky is happening.
        invalid_target_ids = []
        target_ids = []
        sorted_choices = sorted(node.get_choices(), key=lambda t: float(t[0]))
        last_f: float | None = None
        for n, target_id in sorted_choices:
            target_ids.append(target_id)
            if not self._validate_target_id(target_id):
                invalid_target_ids.append(target_id)

            if last_f is None:
                last_f = n
            else:
                if last_f == n:
                    reports.append(
                        InvalidIntervalSameNumberReport(
                            node.id,
                            target_id,
                            n
                        )
                    )
                last_f = n

        # Check for two same edges (e.g. same target_id for 2 or more choices)
        reps = self._validate_target_ids_same_edge(node.id, target_ids)
        if reps:
            reports.extend(reps)

        if len(invalid_target_ids) > 0:
            reports.append(
                InvalidTargetNodeIdReport(node.id, invalid_target_ids)
            )

        # Check if there are any answers at this node
        if len(sorted_choices) == 0:
            reports.append(NoEdgesOnNodeReport(node.id))

        if len(reports) > 0:
            return reports
        else:
            return None

    @staticmethod
    def _validate_end_node(
            node: EndDialogueNode
    ) -> list[AbstractValidationReport] | None:
        # Validate node name
        reports = []
        report = TreeDialogueValidator._validate_node_name(node)
        if report:
            reports.append(report)

        if len(reports) > 0:
            return reports
        else:
            return None

    """
    Cases of validations below shouldn't happen while user is using Dialogue 
    Creator, i.e. someone is trying to mess with our API, these should be 
    clearly visible in Grafana and we should further investigate.
    """

    @staticmethod
    def _validate_node_name(
            node: AbstractDialogueNode
    ) -> InvalidNodeNameReport | None:
        if node.text == "" or node.text is None:
            return InvalidNodeNameReport(node.id, node.text)
        else:
            return None

    def _validate_target_id(self, target_id: int | None) -> bool:
        if target_id is None:
            return False

        nodes = self._tree.get_nodes()
        for node_id, _ in nodes.items():
            if target_id == node_id:
                return True

        return False

    @staticmethod
    def _validate_target_ids_same_edge(
            node_id,
            target_ids: list[int]
    ) -> list[InvalidIntervalSameTargetIdReport]:
        reports: list[InvalidIntervalSameTargetIdReport] = []
        sorted_ids = sorted(target_ids)
        prev_id = None
        for id_ in sorted_ids:
            if prev_id and prev_id == id_:
                reports.append(InvalidIntervalSameTargetIdReport(node_id, id_))
            prev_id = id_

        return reports

    """
    -==========================================================================-
    |                         =<| Graph Traversal |>=                          | 
    -==========================================================================-
    """

    def _mk_graph_data(self):
        """
        We convert our graph dictionary into a more compact representation
        beforehand; this saves us many unnecessary dict look-ups during the
        graph traversal.
        """
        graph_data: dict[int, list[int]] = {}
        for node_id, node in self._tree.get_nodes().items():
            graph_data[node_id] = self._get_target_ids(node)

        return graph_data

    def _check_path_exists(self, to_node: int):
        """
        BFS Graph Traversal. This might be a candidate for FFI rewrite, either
        Rust or old school C. Average Time complexity is O(N+E) where N is
        number of nodes and E is number of edges.

        :param to_node: ID of the node we end the traversal from node with id=1
        :return: True if path to Node with ID=1 is found, False otherwise
        """
        visited_nodes = set()
        queue = deque([(1, [1])])

        while len(queue) != 0:
            (node_id, checked_path) = queue.popleft()

            if node_id not in visited_nodes:
                if node_id == to_node:
                    return True

                visited_nodes.add(node_id)
                ids = self._compact_graph_data.get(node_id)
                if ids:
                    for target_id in ids:
                        if target_id not in visited_nodes:
                            checked_path.append(target_id)
                            queue.append((target_id, checked_path))

        return False

    @staticmethod
    def _get_target_ids(
            node: AbstractDialogueNode
    ) -> list[int | None]  | None:

        if isinstance(node, (ChoiceDialogueNode, QuantifiableDialogueNode)):
            return list(node.get_choices().keys())
        elif isinstance(
                node, (
                        GenericQuestionDialogueNode,
                        SlackUsersChooseDialogueNode
                )
        ):
            return [node.next_node] if node.next_node is not None else []
        elif isinstance(node, IntervalDialogueNode):
            return [target_id for _, target_id in node.get_choices()]
        elif isinstance(node, EndDialogueNode):
            l: list[int] = []
            return l
