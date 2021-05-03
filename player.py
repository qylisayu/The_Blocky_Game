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
Misha Schwartz, and Jaisie Sin.

=== Module Description ===

This file contains the hierarchy of player classes.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
import random
import pygame

from block import Block
from goal import Goal, generate_goals

from actions import KEY_ACTION, SMASH, PASS, PAINT, COMBINE


def create_players(num_human: int, num_random: int, smart_players: List[int]) \
        -> List[Player]:
    """Return a new list of Player objects.

    <num_human> is the number of human player, <num_random> is the number of
    random players, and <smart_players> is a list of difficulty levels for each
    SmartPlayer that is to be created.

    The list should contain <num_human> HumanPlayer objects first, then
    <num_random> RandomPlayer objects, then the same number of SmartPlayer
    objects as the length of <smart_players>. The difficulty levels in
    <smart_players> should be applied to each SmartPlayer object, in order.
    """
    # TODO: Implement Me
    # -RT -F
    humans = [HumanPlayer(i, generate_goals(1)[0]) for i in range(num_human)]
    randoms = [RandomPlayer(i + num_human, generate_goals(1)[0]) for i in
               range(num_random)]
    smarts = [SmartPlayer(i + num_human + num_random, generate_goals(1)[0],
                          smart_players[i]) for i in range(len(smart_players))]
    return humans + randoms + smarts


def _get_block(block: Block, location: Tuple[int, int], level: int) -> \
        Optional[Block]:
    """Return the Block within <block> that is at <level> and includes
    <location>. <location> is a coordinate-pair (x, y).

    A block includes all locations that are strictly inside of it, as well as
    locations on the top and left edges. A block does not include locations that
    are on the bottom or right edge.

    If a Block includes <location>, then so do its ancestors. <level> specifies
    which of these blocks to return. If <level> is greater than the level of
    the deepest block that includes <location>, then return that deepest block.

    If no Block can be found at <location>, return None.

    Preconditions:
        - 0 <= level <= max_depth
    """
    # TODO: Implement me
    # -RT -F
    x, y = location
    bx, by = block.position
    size = block.size
    if not (bx <= x < bx + size and by <= y < by + size):
        return None
    in_blocks = [_get_block(c, location, level) for c in block.children]
    return block if level == block.level or not block.children else next((
        b for b in in_blocks if b), block)
    # Iteration shouldn't end, but set block as default value just in case


class Player:
    """A player in the Blocky game.

    This is an abstract class. Only child classes should be instantiated.

    === Public Attributes ===
    id:
        This player's number.
    goal:
        This player's assigned goal for the game.
    """
    id: int
    goal: Goal

    def __init__(self, player_id: int, goal: Goal) -> None:
        """Initialize this Player.
        """
        self.goal = goal
        self.id = player_id

    def get_selected_block(self, board: Block) -> Optional[Block]:
        """Return the block that is currently selected by the player.

        If no block is selected by the player, return None.
        """
        raise NotImplementedError

    def process_event(self, event: pygame.event.Event) -> None:
        """Update this player based on the pygame event.
        """
        raise NotImplementedError

    def generate_move(self, board: Block) -> \
            Optional[Tuple[str, Optional[int], Block]]:
        """Return a potential move to make on the game board.

        The move is a tuple consisting of a string, an optional integer, and
        a block. The string indicates the move being made (i.e., rotate, swap,
        or smash). The integer indicates the direction (i.e., for rotate and
        swap). And the block indicates which block is being acted on.

        Return None if no move can be made, yet.
        """
        raise NotImplementedError


def _create_move(action: Tuple[str, Optional[int]], block: Block) -> \
        Tuple[str, Optional[int], Block]:
    return action[0], action[1], block


class HumanPlayer(Player):
    """A human player.
    """
    # === Private Attributes ===
    # _level:
    #     The level of the Block that the user selected most recently.
    # _desired_action:
    #     The most recent action that the user is attempting to do.
    #
    # == Representation Invariants concerning the private attributes ==
    #     _level >= 0
    _level: int
    _desired_action: Optional[Tuple[str, Optional[int]]]

    def __init__(self, player_id: int, goal: Goal) -> None:
        """Initialize this HumanPlayer with the given <renderer>, <player_id>
        and <goal>.
        """
        Player.__init__(self, player_id, goal)

        # This HumanPlayer has not yet selected a block, so set _level to 0
        # and _selected_block to None.
        self._level = 0
        self._desired_action = None

    def get_selected_block(self, board: Block) -> Optional[Block]:
        """Return the block that is currently selected by the player based on
        the position of the mouse on the screen and the player's desired level.

        If no block is selected by the player, return None.
        """
        mouse_pos = pygame.mouse.get_pos()
        block = _get_block(board, mouse_pos, self._level)
        return block

    def process_event(self, event: pygame.event.Event) -> None:
        """Respond to the relevant keyboard events made by the player based on
        the mapping in KEY_ACTION, as well as the W and S keys for changing
        the level.
        """
        if event.type == pygame.KEYDOWN:
            if event.key in KEY_ACTION:
                self._desired_action = KEY_ACTION[event.key]
            elif event.key == pygame.K_w:
                self._level = max(0, self._level - 1)
                self._desired_action = None
            elif event.key == pygame.K_s:
                self._level += 1
                self._desired_action = None

    def generate_move(self, board: Block) -> \
            Optional[Tuple[str, Optional[int], Block]]:
        """Return the move that the player would like to perform. The move may
        not be valid.

        Return None if the player is not currently selecting a block.
        """
        block = self.get_selected_block(board)

        if block is None or self._desired_action is None:
            return None
        else:
            move = _create_move(self._desired_action, block)

            self._desired_action = None
            return move


class RandomPlayer(Player):
    """
    A player that randomly chooses a move other than PASS.

    === Public Attributes ===
    id:
        This player's number.
    goal:
        This player's assigned goal for the game.

     === Private Attributes ===
     _proceed:
       True when the player should make a move, False when the player should
       wait.
    """
    _proceed: bool

    def __init__(self, player_id: int, goal: Goal) -> None:
        super().__init__(player_id, goal)
        self._proceed = False

    def get_selected_block(self, board: Block) -> Optional[Block]:
        return None

    def process_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._proceed = True

    def _random_move(self, board: Block) \
            -> Tuple[int, Tuple[Tuple[str, Optional[int]], Block]]:
        """
        Generates a valid random move based on <board> and returns the potential
        score and move on a block as a tuple.


        >>> b = Block((0, 0), 10, (0, 0, 0), 0, 1)
        >>> move = RandomPlayer(0, generate_goals(1)[0])._random_move(b)[1][0]
        >>> move in (SMASH, PAINT, PASS)
        True
        """
        # -F
        # There's a million ways to implement this and the way
        # I did it is honestly not great, but w/e
        x, y = board.position
        board_ = board.create_copy()
        successful = False
        action_, block = None, None
        # Keep trying to make a move until it's successful
        while not successful:
            # Randomize a mouse position
            mouse_pos = (random.randint(x, x + board.size - 1),
                         random.randint(y, y + board.size - 1))
            level = random.randint(0, board.max_depth)
            # Get the block and copy block at the mouse pos
            block_ = _get_block(board_, mouse_pos, level)
            block = _get_block(board, mouse_pos, level)
            # Create the list of possible moves
            allowed = list(KEY_ACTION.values())
            # Make the choice of a random action
            action_ = random.choice(allowed)
            # This if statement should never execute, but it
            # acts as a safeguard
            if block_ is None or block_ != block:
                continue
            if action_ == PASS:
                return self.goal.score(board_), (action_, block)
            do = getattr(block_, action_[0])
            if action_ in (SMASH, COMBINE):
                successful = do()
            elif action_ == PAINT:
                successful = do(self.goal.colour)
            else:
                successful = do(action_[1])
        return self.goal.score(board_), (action_, block)

    def generate_move(self, board: Block) ->\
            Optional[Tuple[str, Optional[int], Block]]:
        """Return a valid, randomly generated move.

        A valid move is a move other than PASS that can be successfully
        performed on the <board>.

        This function does not mutate <board>.
        """
        # -RT -F
        if not self._proceed:
            return None  # Do not remove

        action, block = self._random_move(board)[1]
        while action == PASS:
            action, block = self._random_move(board)[1]
        self._proceed = False  # Must set to False before returning!
        return _create_move(action, block)


class SmartPlayer(RandomPlayer):
    """
    A smart player that tries to make the best move it can find.

    === Public Attributes ===
    id:
        This player's number.
    goal:
        This player's assigned goal for the game.
    difficulty:
        A value corresponding to how well this player will play.

     === Private Attributes ===
     _proceed:
       True when the player should make a move, False when the player should
       wait.
    """
    _proceed: bool
    difficulty: int

    def __init__(self, player_id: int, goal: Goal, difficulty: int) -> None:
        super().__init__(player_id, goal)
        self.difficulty = difficulty

    def get_selected_block(self, board: Block) -> Optional[Block]:
        return None

    def process_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._proceed = True

    def generate_move(self, board: Block) ->\
            Optional[Tuple[str, Optional[int], Block]]:
        """Return a valid move by assessing multiple valid moves and choosing
        the move that results in the highest score for this player's goal (i.e.,
        disregarding penalties).

        A valid move is a move other than PASS that can be successfully
        performed on the <board>. If no move can be found that is better than
        the current score, this player will pass.

        This function does not mutate <board>.
        """
        # -RT -F
        if not self._proceed:
            return None  # Do not remove

        scores = tuple(self._random_move(board) for _ in range(self.difficulty))
        score, (move, block) = max((s for s in scores), key=lambda p: p[0])
        curr_score = self.goal.score(board)
        if score <= curr_score:
            move, block = PASS, board
        self._proceed = False  # Must set to False before returning!
        return _create_move(move, block)


if __name__ == '__main__':
    import python_ta

    python_ta.check_all(config={
        'allowed-io': ['process_event'],
        'allowed-import-modules': [
            'doctest', 'python_ta', 'random', 'typing', 'actions', 'block',
            'goal', 'pygame', '__future__'
        ],
        'max-attributes': 10,
        'generated-members': 'pygame.*'
    })
