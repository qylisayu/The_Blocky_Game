from typing import List, Optional, Tuple
import os
import pygame
import pytest

from block import Block, generate_board
from blocky import _block_to_squares, GameData, GameState, MainState
from goal import BlobGoal, PerimeterGoal, _flatten
from player import _get_block, create_players
from renderer import Renderer
from settings import COLOUR_LIST, BACKGROUND_COLOUR, colour_name, BOARD_SIZE
import random
import math
import threading
import time
import logging

pygame.init()
pygame.font.init()


def set_children(block: Block, colours: List[Optional[Tuple[int, int, int]]]) \
        -> None:
    """Set the children at <level> for <block> using the given <colours>.

    Precondition:
        - len(colours) == 4
        - block.level + 1 <= block.max_depth
    """
    size = block._child_size()
    positions = block._children_positions()
    level = block.level + 1
    depth = block.max_depth

    block.children = []  # Potentially discard children
    for i in range(4):
        b = Block(positions[i], size, colours[i], level, depth)
        block.children.append(b)


def board_16x16() -> Block:
    """Create a reference board with a size of 750 and a max_depth of 2.
    """
    # Level 0
    board = Block((0, 0), 750, None, 0, 2)

    # Level 1
    colours = [None, COLOUR_LIST[2], COLOUR_LIST[1], COLOUR_LIST[3]]
    set_children(board, colours)

    # Level 2
    colours = [COLOUR_LIST[0], COLOUR_LIST[1], COLOUR_LIST[1], COLOUR_LIST[3]]
    set_children(board.children[0], colours)

    return board


def generate_board(max_depth, size=750, children=False):
    if not children:
        return Block((0, 0), size, random.choice(COLOUR_LIST), 0, max_depth)
    b = Block((0, 0), size, None, 0, max_depth)
    set_children(b, COLOUR_LIST)
    return b


def _guarantee_smash(block):
    if not block or not block.smashable():
        return
    block.colour = None
    child_size = block._child_size()
    next_level = block.level + 1
    block.children = [
        Block(pos, child_size, random.choice(COLOUR_LIST), next_level,
              block.max_depth) for pos in block._children_positions()]


def smash_all(block):
    _guarantee_smash(block)
    if not block.children:
        return
    for b in block.children:
        smash_all(b)


class DebugMode:

    def __init__(self, board, routines=None):
        self.board = board
        self._routines = [] if routines is None else routines
        self._level = 0
        self.colour = COLOUR_LIST[0]
        self.thread_stop = False
        self.thread = None
        self.render_buffer = []
        self.demonstration = None
        self._demo_delay = 250
        self._keybinds = {pygame.K_k: smash_all,
                          pygame.K_r: self._paint,
                          pygame.K_j: self._paint_all,
                          pygame.K_SPACE: lambda block: block.smash(),
                          pygame.K_c: lambda block: block.combine(),
                          pygame.K_e: lambda block: block.swap(1),
                          pygame.K_q: lambda block: block.swap(0),
                          pygame.K_a: lambda block: block.rotate(3),
                          pygame.K_d: lambda block: block.rotate(1)}

    def display(self):
        self._kill_thread()
        self.thread = threading.Thread(target=self._threaded_display,
                                       daemon=True)
        self.thread.start()

    def _kill_thread(self):
        if self.thread is not None and self.thread.is_alive():
            self.thread_stop = True
            time.sleep(0.5)
            self.thread.join()
            self.thread_stop = False
            self.thread = None

    def add_routine(self, routine):
        self._routines.append(routine)

    def remove_routine(self, routine):
        self._routines.remove(routine)

    def _highlight(self, renderer):
        mouse_pos = pygame.mouse.get_pos()
        block = _get_block(self.board, mouse_pos, self._level)
        if block is not None:
            renderer.highlight_block(block.position, block.size)

    def _increment_colour(self, dir_):
        self.colour = COLOUR_LIST[
            (COLOUR_LIST.index(self.colour) + dir_) % len(COLOUR_LIST)]

    def _paint(self, block):
        if block.children:
            return
        block.colour = self.colour

    def _paint_all(self, block):
        if not block.children:
            block.colour = self.colour
        for c in block.children:
            self._paint_all(c)

    def _mouse_cursor(self, renderer):
        pos = pygame.mouse.get_pos()
        pygame.draw.circle(renderer._screen, self.colour, pos, 15)
        pygame.draw.circle(renderer._screen, (0, 0, 0), pos, 15, 2)

    def _threaded_display(self):
        print('Initialized thread.\n')
        pygame.quit()
        pygame.font.init()
        renderer = Renderer(self.board.size)
        clock = pygame.time.Clock()
        pygame.mouse.set_visible(False)
        while not self.thread_stop:
            clock.tick(60)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    print('Thread terminated.\n')
                    return
                if e.type == pygame.KEYDOWN:
                    block = _get_block(self.board, pygame.mouse.get_pos(),
                                       self._level)
                    if block and self._keybinds.get(e.key, None):
                        self._keybinds.get(e.key)(block)
                    elif e.key == pygame.K_w:
                        self._level = self._level - 1 if self._level > 0 else 0
                    elif e.key == pygame.K_s:
                        self._level += 1
                    elif e.key == pygame.K_1:
                        self._increment_colour(-1)
                    elif e.key == pygame.K_2:
                        self._increment_colour(1)
                    elif e.key == pygame.K_p:
                        print(f'{colour_name(self.colour)} perimeter score: '
                              f'{PerimeterGoal(self.colour).score(self.board)}')
                    elif e.key == pygame.K_b:
                        print(f'{colour_name(self.colour)} blob score: '
                              f'{BlobGoal(self.colour).score(self.board)}')
                if e.type == pygame.MOUSEBUTTONDOWN and not self.render_buffer:
                    self._demo()
            renderer._screen.fill(BACKGROUND_COLOUR)
            renderer.draw_board(_block_to_squares(self.board))
            for coroutine in self._routines:
                coroutine(self.board, renderer)
            if self._draw_from_bfr(renderer):
                pygame.time.wait(self._demo_delay)
            else:
                self._highlight(renderer)
                self._mouse_cursor(renderer)
            pygame.display.flip()
        print('Terminated thread.\n')

    def _draw_from_bfr(self, renderer):
        if self.render_buffer:
            pos, size, colour = self.render_buffer.pop(0)
            rect = (pos[0], pos[1], size, size)
            pygame.draw.rect(renderer._screen, colour, rect, width=5)
            if not self.render_buffer:
                renderer.print("Finished Demo", 0, 0)
                pygame.display.flip()
                pygame.time.wait(1000)
            return True
        return False

    def _demo(self):
        if self.demonstration is not None:
            it = self.demonstration(self.board)
            n = next(it, None)
            while n is not None:
                self.render_buffer.append(n)
                n = next(it, None)


class DebugGame:

    def __init__(self, max_depth, num_human, num_random, smart_players) -> None:

        board = generate_board(max_depth, BOARD_SIZE)
        players = create_players(num_human, num_random, smart_players)

        self._data = GameData(board, players)
        self._state = MainState(self._data)
        self.thread = None
        self.thread_stop = False

    def start_game(self, target=None, turns=10):
        if target is None:
            return
        self._kill_thread()
        self.thread = threading.Thread(target=lambda: self.auto_run_game(turns), daemon=True)
        self.thread.start()

    def _kill_thread(self):
        if self.thread is not None and self.thread.is_alive():
            self.thread_stop = True
            time.sleep(0.5)
            self.thread.join()
            self.thread_stop = False
            pygame.quit()
            pygame.init()
            self.thread = None

    def run_game(self, num_turns):
        self._data.max_turns = num_turns
        renderer = Renderer(BOARD_SIZE)
        clock = pygame.time.Clock()
        while not self.thread_stop:
            clock.tick(30)

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    return
                else:
                    self._state.process_event(e)
            self._state = self._state.update()
            renderer.clear()
            self._state.render(renderer)
            pygame.display.flip()

    def auto_run_game(self, num_turns):
        print('Initialized thread.')
        renderer = Renderer(BOARD_SIZE)
        self._data.max_turns = num_turns
        clock = pygame.time.Clock()
        while not self.thread_stop:
            clock.tick(144)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    return
            if isinstance(self._state, MainState):
                self._state._current_player().process_event(
                    pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))
            self._state = self._state.update()
            renderer.clear()
            self._state.render(renderer)
            pygame.display.flip()
        print('Terminated thread.')


def display_flatten(board, renderer):
    flat = _flatten(board)
    grid_size = board.size / (math.pow(2, board.max_depth))
    ox, oy = board.position
    for i in range(len(flat)):
        for j in range(len(flat[i])):
            s = pygame.font.SysFont('Arial', 12).render(colour_name(flat[j][i]),
                                                        True,
                                                        (0, 0, 0))
            renderer._screen.blit(s, (j * grid_size + ox + grid_size / 6,
                                      i * grid_size + oy + grid_size / 4))


def display_perimeter(board, renderer):
    flat = _flatten(board)
    grid_size = math.ceil(board.size / (math.pow(2, board.max_depth)))
    size = len(flat)
    ox, oy = board.position
    for p in range(size):
        renderer.highlight_block((ox, p * grid_size + oy), grid_size)
        renderer.highlight_block((p * grid_size + ox, oy), grid_size)
        renderer.highlight_block(
            (board.size + ox - grid_size, p * grid_size + oy), grid_size)
        renderer.highlight_block(
            (p * grid_size + ox, board.size + oy - grid_size), grid_size)


def demo_blob(board):
    flat = _flatten(board)
    visited = [[-1 for _ in range(len(flat))] for _ in range(len(flat))]
    size = len(flat)
    grid_size = math.ceil(board.size / (math.pow(2, board.max_depth)))
    dim2_iter = [(x, y) for x in range(size) for y in range(size)]
    ox, oy = board.position
    for x, y in dim2_iter:
        blob = _undiscovered_blob((x, y), flat, visited)
        for bx, by, colour in blob:
            yield (ox + bx * grid_size, oy + by * grid_size), grid_size, colour
    yield None


def _undiscovered_blob(pos, board, visited):
    x, y = pos
    if not (0 <= x < len(board) and 0 <= y < len(board)) \
            or not visited[x][y] == -1:
        return []
    if not board[x][y] == COLOUR_LIST[0]:
        visited[x][y] = 0
        return [(x, y, (255, 0, 0))]
    visited[x][y] = 1
    lst = [(x, y, (0, 255, 0))]
    for i in (-1, 1):
        lst.extend(_undiscovered_blob((x, y + i), board, visited))
        lst.extend(_undiscovered_blob((x + i, y), board, visited))
    return lst


def demo_perimeter(board):
    flat = _flatten(board)
    size = len(flat)
    grid_size = math.ceil(board.size / (math.pow(2, board.max_depth)))
    ox, oy = board.position
    for p in range(size):
        colour = COLOUR_LIST[0]
        pass_ = (0, 255, 0)
        fail_ = (255, 0, 0)
        if flat[0][p] == colour:
            yield (ox, oy + p * grid_size), grid_size, pass_
        else:
            yield (ox, oy + p * grid_size), grid_size, fail_
        if flat[p][0] == colour:
            yield (ox + p * grid_size, oy), grid_size, pass_
        else:
            yield (ox + p * grid_size, oy), grid_size, fail_
        if flat[size - 1][p] == colour:
            yield (ox + (size - 1) * grid_size,
                   oy + p * grid_size), grid_size, pass_
        else:
            yield (ox + (size - 1) * grid_size,
                   oy + p * grid_size), grid_size, fail_
        if flat[p][size - 1] == colour:
            yield (ox + p * grid_size,
                   oy + (size - 1) * grid_size), grid_size, pass_
        else:
            yield (ox + p * grid_size,
                   oy + (size - 1) * grid_size), grid_size, fail_


if __name__ == '__main__':
    debug = DebugMode(generate_board(3, children=True))
    print('Started')
    while True:
        command = input('')
        try:
            exec(command)
        except Exception as e:
            print(f'Failed: {e}')
