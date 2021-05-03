"""CSC148 Assignment 2

=== CSC148 Winter 2020 ===
Department of Computer Science,
University of Toronto

This code is provided solely for the personal and private use of
students taking the CSC148 course at the University of Toronto.
Copying for purposes other than this use is expressly prohibited.
All forms of distribution of this code, whether as given or with
any changes, are expressly prohibited.

Authors: Diane Horton, David Liu, Mario Badr, Sophia Huynh, Misha Schwartz,
and Jaisie Sin

All of the files in this directory and all subdirectories are:
Copyright (c) Diane Horton, David Liu, Mario Badr, Sophia Huynh,
Misha Schwartz, and Jaisie Sin

=== Module Description ===

This file contains the hierarchy of Goal classes.
"""
from __future__ import annotations
import math
import random
from typing import List, Tuple
from block import Block
from settings import colour_name, COLOUR_LIST


def generate_goals(num_goals: int) -> List[Goal]:
    """Return a randomly generated list of goals with length num_goals.

    All elements of the list must be the same type of goal, but each goal
    must have a different randomly generated colour from COLOUR_LIST. No two
    goals can have the same colour.

    Precondition:
        - num_goals <= len(COLOUR_LIST)
    """
    # TODO: Implement Me
    # -RT -F
    goal_choice = random.choice([True, False])
    random_colours = COLOUR_LIST[:]
    random.shuffle(random_colours)
    return [(PerimeterGoal(random_colours[i]) if goal_choice else BlobGoal(
        random_colours[i])) for i in range(num_goals)]


def _flatten(block: Block) -> List[List[Tuple[int, int, int]]]:
    """Return a two-dimensional list representing <block> as rows and columns of
    unit cells.

    Return a list of lists L, where,
    for 0 <= i, j < 2^{max_depth - self.level}
        - L[i] represents column i and
        - L[i][j] represents the unit cell at column i and row j.

    Each unit cell is represented by a tuple of 3 ints, which is the colour
    of the block at the cell location[i][j]

    L[0][0] represents the unit cell in the upper left corner of the Block.
    """
    # *** -RT ***
    # I remember this wasn't that easy, but I am very confident it works,
    # though we should definitely test this rigorously anyways.
    size = int(math.pow(2, block.max_depth - block.level))
    if not block.children or size == 1:
        return [[block.colour for _ in range(size)] for _ in range(size)]
    flattened = [_flatten(block.children[i]) for i in
                 range(len(block.children))]
    left = [i + j for i, j in zip(flattened[1], flattened[2])]
    right = [i + j for i, j in zip(flattened[0], flattened[3])]
    return left + right


class Goal:
    """A player goal in the game of Blocky.

    This is an abstract class. Only child classes should be instantiated.

    === Attributes ===
    colour:
        The target colour for this goal, that is the colour to which
        this goal applies.
    """
    colour: Tuple[int, int, int]

    def __init__(self, target_colour: Tuple[int, int, int]) -> None:
        """Initialize this goal to have the given target colour.
        """
        self.colour = target_colour

    def score(self, board: Block) -> int:
        """Return the current score for this goal on the given board.

        The score is always greater than or equal to 0.
        """
        raise NotImplementedError

    def description(self) -> str:
        """Return a description of this goal.
        """
        raise NotImplementedError


class PerimeterGoal(Goal):
    """A player goal in the game of Blocky that scores based on the
    number of coloured unity blocks on the perimeter of the board that
    match this instance's colour.

    === Attributes ===
    colour:
        The target colour for this goal, that is the colour to which
        this goal applies.
    """
    def score(self, board: Block) -> int:
        # -RT -F
        flat = _flatten(board)
        size = len(flat)
        # Iterate over the four corners to the the next corner
        perimeter = [
            (flat[0][p], flat[p][0], flat[size - 1][p], flat[p][size - 1]) for
            p in range(size)]
        # Take the sum of the number of times the colour has occurred
        score = sum(map(lambda p: p.count(self.colour), perimeter))
        return score

    def description(self) -> str:
        # -F
        return f'Aim to get as many {colour_name(self.colour)} blocks by the ' \
               f'perimeter of the board!'


class BlobGoal(Goal):
    """A player goal in the game of Blocky that scores based on the
    largest amount of connected unit blocks.

    === Attributes ===
    colour:
        The target colour for this goal, that is the colour to which
        this goal applies.
    """
    def score(self, board: Block) -> int:
        flat = _flatten(board)
        # Create a list of the visited blocks
        visited = [[-1 for _ in range(len(flat))] for _ in range(len(flat))]
        size = len(flat)
        # Create an iterable that iterates through the nxn board
        dim2_iter = [(x, y) for x in range(size) for y in range(size)]
        # Iterate through the 2D iterable and get the max
        score = max(self._undiscovered_blob_size((x, y), flat, visited)
                    for x, y in dim2_iter)
        return score

    def _undiscovered_blob_size(self, pos: Tuple[int, int],
                                board: List[List[Tuple[int, int, int]]],
                                visited: List[List[int]]) -> int:
        """Return the size of the largest connected blob that (a) is of this
        Goal's target colour, (b) includes the cell at <pos>, and (c) involves
        only cells that have never been visited.

        If <pos> is out of bounds for <board>, return 0.

        <board> is the flattened board on which to search for the blob.
        <visited> is a parallel structure that, in each cell, contains:
            -1 if this cell has never been visited
            0  if this cell has been visited and discovered
               not to be of the target colour
            1  if this cell has been visited and discovered
               to be of the target colour

        Update <visited> so that all cells that are visited are marked with
        either 0 or 1.
        """
        x, y = pos
        # If position isn't in bound or pos has already been visited, return 0.
        if not (0 <= x < len(board) and 0 <= y < len(board)) \
                or not visited[x][y] == -1:
            return 0
        # If position in bound and pos hasn't been visited, but not right 
        # colour,
        # mark visited with the wrong colour and return 0.
        if not board[x][y] == self.colour:
            visited[x][y] = 0
            return 0
        # Mark visited as the correct colour and set count to 1.
        visited[x][y] = count = 1
        # Recursively call on the adjacent blocks and add to count.
        for i in (-1, 1):
            count += self._undiscovered_blob_size((x, y + i), board, visited) \
                + self._undiscovered_blob_size((x + i, y), board, visited)
        return count

    def description(self) -> str:
        # -F
        return f'Aim to get the largest group of connected ' \
               f'{colour_name(self.colour)} blocks!'


if __name__ == '__main__':
    import python_ta
    python_ta.check_all(config={
        'allowed-import-modules': [
            'doctest', 'python_ta', 'random', 'typing', 'block', 'settings',
            'math', '__future__'
        ],
        'max-attributes': 15
    })
