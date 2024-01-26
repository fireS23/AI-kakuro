from partitioner import Partitioner
import operator
import sample_kakuro_puzzles
import sys
import math
import time
import os
from copy import deepcopy
from numpy import random


class Utils:
    # DEFAULT DISPLAY SETTINGS
    COLORS = {'RED': '\033[91m', 'EMERALD': '\033[92m', 'YELLOW': '\033[93m',
            'BLUE1': '\033[94m', 'PINK': '\033[95m', 'BLUE2': '\033[96m', 'WHITE': '\033[97m'}
    BLOCK_STYLE = '\u25A0'
    COLOR_LAST_ASSIGNMENT = COLORS['RED']
    COLOR_H = COLORS['YELLOW']
    COLOR_V = COLORS['BLUE2']
    COLOR_SEP = COLORS['WHITE']
    END_COLOR = '\033[0m'
    EMPTY_TILE = '\u002D'

    @staticmethod
    def set_display_settings(block_style, block_thickness=3, h_color=COLOR_H, v_color=COLOR_V, sep_color=COLOR_SEP):
        if block_style == 'highlight':
            Utils.BLOCK_STYLE = '\033[107m' + ' ' * block_thickness + '\033[0m'
        elif block_style == 'filled-square':
            Utils.BLOCK_STYLE = '\u25A0'
        Utils.COLOR_H = Utils.COLORS[h_color]
        Utils.COLOR_V = Utils.COLORS[v_color]
        Utils.COLOR_SEP = Utils.COLORS[sep_color]

    @staticmethod
    def update_board(assignments, new_assignment={}, highlight_latest_assignment=True):
        updated_board = deepcopy(Kakuro.STARTING_BOARD)
        for tile, val in assignments.items():
            row = tile.row
            col = tile.col
            updated_board[row][col] = str(val)
        if highlight_latest_assignment:
            for tile, val in new_assignment.items():
                row = tile.row
                col = tile.col
                updated_board[row][col] = Utils.COLOR_LAST_ASSIGNMENT + str(val) + Utils.END_COLOR
        return updated_board

    @staticmethod
    def print_board(board_display_matrix):
        for i in board_display_matrix:
            print('\t'.join(map(str, i)))


class Kakuro:
    VARIABLE_COUNT = 0
    STARTING_BOARD = []

    class Tile:
        def __init__(self, row, col):
            self.row = row
            self.col = col
            self.hgroup = None
            self.vgroup = None

        def get_group(self, orientation):
            if orientation == 0:
                return self.hgroup
            else:
                return self.vgroup

        def __str__(self):
            return f'[{self.row},{self.col}]'

        def __repr__(self):
            return self.__str__()

        @staticmethod
        def get_tile(row, col, tile_list):
            for tile in tile_list:
                if (row == tile.row) and (col == tile.col):
                    return tile

    class Group:
        def __init__(self, rule, tiles):
            self.rule = rule
            self.tiles = tiles
            self.ratio = 0

        def pre_calculate(self, assignments):
            updated_rule = self.rule
            unassigned_tile_count = len(self.tiles)
            assigned_tile_count = 0
            for tile in self.tiles:
                if tile in assignments:
                    updated_rule -= assignments[tile]
                    assigned_tile_count += 1
            unassigned_tile_count -= assigned_tile_count
            return unassigned_tile_count, assigned_tile_count, updated_rule

        def calculate_unordered_ratio(self, new_assignment_val, unassigned_tile_count, assigned_tile_count, updated_rule):
            current_rule = updated_rule - new_assignment_val
            utc_new = unassigned_tile_count - 1
            atc_new = assigned_tile_count + 1
            if utc_new == 0:
                return 0, 0
            else:
                rule_over_tile_count = current_rule / utc_new
                return (9 - atc_new / 9) * min(9 - rule_over_tile_count, rule_over_tile_count - 1), atc_new

        def calculate_ratio(self, assignments):
            updated_rule = self.rule
            updated_tile_count = len(self.tiles)
            for tile in self.tiles:
                if tile in assignments:
                    updated_rule -= assignments[tile]
                    updated_tile_count -= 1
            if updated_tile_count == 0:
                self.ratio = 999
            else:
                rule_over_tile_count = updated_rule / updated_tile_count
                self.ratio = math.factorial(updated_tile_count) * min((9 - rule_over_tile_count),
                                                                      rule_over_tile_count - 1)
                return self

        def generate_domain(self, assignments):
            reduced_tile_count = len(self.tiles)
            reduced_rule = self.rule
            unassigned_tiles = []
            used_digits = set()
            for tile in self.tiles:
                if tile in assignments:
                    reduced_tile_count -= 1
                    digit = assignments[tile]
                    reduced_rule -= digit
                    used_digits.add(digit)
                else:
                    unassigned_tiles.append(tile)

            partitions = Partitioner.get_ordered_partitions(reduced_rule, reduced_tile_count)

            for p in partitions.copy():
                if len(set(p) | used_digits) < len(p) + len(used_digits):
                    partitions.remove(p)

            if reduced_rule == 0 and reduced_tile_count == 0:
                single_val_domain = [assignments[tile] for tile in self.tiles]
                partitions = [single_val_domain]
            return partitions, unassigned_tiles

        def get_unassigned_tiles(self, assignments):
            unassigned_tiles = []
            for tile in self.tiles:
                if tile in assignments:
                    unassigned_tiles.append(tile)
            return unassigned_tiles

        def create_ordered_domain(self, unordered_partitions, unassigned_tiles, assignments):
            # determine orientation of affected (perpendicular) groups. '1' is vertical.
            if self.tiles[0].row - self.tiles[1].row == 0:
                orientation = 1
            else:
                orientation = 0

            scored_partitions = []

            affected_groups = [t.get_group(orientation) for t in unassigned_tiles]
            affected_groups_params = []
            for g in affected_groups:
                params = g.pre_calculate(assignments)
                affected_groups_params.append(params)

            for partition in unordered_partitions:
                score = 0
                for i in range(len(partition)):
                    ratio, unassigned_tile_count = affected_groups[i].calculate_unordered_ratio(partition[i],
                                                                                                affected_groups_params[i][0],
                                                                                                affected_groups_params[i][1],
                                                                                                affected_groups_params[i][
                                                                                                    2])
                    score += ratio * math.factorial(unassigned_tile_count)
                scored_partitions.append(tuple([partition, score]))
            scored_partitions.sort(key=operator.itemgetter(1), reverse=True)
            return [x[0] for x in scored_partitions]

        def __str__(self):
            string = f'Group ID: {self.id}-{self.orientation}\nRule = {self.rule}\nTiles = {self.tiles}\n'
            if self.ratio != 0:
                string += f'Ratio = {self.ratio}\n'
            return string

        def __repr__(self):
            return self.__str__()

    def __init__(self, groups):
        self.groups = groups
        Kakuro.VARIABLE_COUNT += sum([len(g.tiles) for g in groups[0]])

    @staticmethod
    def create_board_from_string(board_size, board_str):
        board_display_matrix = [[Utils.BLOCK_STYLE] * board_size for _ in range(board_size)]
        h_groups_string, v_groups_string = board_str.split(sep=';')
        all_tiles = []

        # Create horizontal groups
        h_group_list = h_groups_string.split(sep=',')
        h_groups = []
        for h_group_condensed in h_group_list:
            h = [int(x) for x in h_group_condensed.split(sep=' ')]
            board_display_matrix[h[0]][h[1] - 1] = Utils.COLOR_SEP + '/' + Utils.COLOR_H + str(h[3]) + Utils.END_COLOR
            h_tiles = []
            h_rule = h[3]
            for i in range(h[1], h[2] + 1):
                board_display_matrix[h[0]][i] = Utils.EMPTY_TILE
                h_tiles.append(Kakuro.Tile(h[0], i))
            h_groups.append(Kakuro.Group(h_rule, h_tiles))
            for tile in h_tiles:
                tile.hgroup = h_groups[-1]
            all_tiles = all_tiles + h_tiles

        # Create vertical groups
        v_group_list = v_groups_string.split(sep=',')
        v_groups = []
        for v_group_condensed in v_group_list:
            v = [int(x) for x in v_group_condensed.split(sep=' ')]
            if board_display_matrix[v[1] - 1][v[0]] == Utils.BLOCK_STYLE:
                board_display_matrix[v[1] - 1][v[0]] = Utils.COLOR_V + str(v[3]) + Utils.COLOR_SEP + '/' + Utils.END_COLOR
            else:
                board_display_matrix[v[1] - 1][v[0]] = Utils.COLOR_V + str(v[3]) + board_display_matrix[v[1] - 1][v[0]]
            v_tiles = []
            v_rule = v[3]
            for i in range(v[1], v[2] + 1):
                v_tiles.append(Kakuro.Tile.get_tile(i, v[0], all_tiles))
                board_display_matrix[i][v[0]] = Utils.EMPTY_TILE
            v_groups.append(Kakuro.Group(v_rule, v_tiles))
            for tile in v_tiles:
                tile.vgroup = v_groups[-1]
            groups = [h_groups]
            groups.append(v_groups)
        return Kakuro(groups), board_display_matrix

    def get_unassigned_groups(self, assignments):
        unassigned_groups = []
        for group_type in self.groups:
            for group in group_type:
                assigned = True
                for tile in group.tiles:
                    if tile not in assignments:
                        assigned = False
                        break
                if not assigned:
                    unassigned_groups.append(group)
        return unassigned_groups

    def calculate_ratios(self, assignments):
        unassigned_groups = []
        for g_list in self.groups:
            for g in g_list:
                group = g.calculate_ratio(assignments)
                if group is not None:
                    unassigned_groups.append(group)
        return unassigned_groups

    @staticmethod
    def select_most_constrained_group(unassigned_groups) -> Group:
        return min(unassigned_groups, key=operator.attrgetter('ratio'))

    @staticmethod
    def check_assignment_completeness(assignments) -> bool:
        if len(assignments) == Kakuro.VARIABLE_COUNT:
            return True
        else:
            return False

    def check_current_consistency(self, assignments, last_assignment):
        for tile, val in last_assignment.items():
            related_groups = [tile.hgroup] + [tile.vgroup]
            for group in related_groups:
                for group_tile in group.tiles:
                    if group_tile in assignments:
                        if assignments[group_tile] == val:
                            return False
        return True

    def solve(self, assignments={}, use_MCV=False, use_LCV=False):
        # Check if assignment is complete
        if Kakuro.check_assignment_completeness(assignments):
            return assignments

        # Choose variables based on strategy
        if use_MCV:
            selected_group = Kakuro.select_most_constrained_group(self.calculate_ratios(assignments))
        else:
            selected_group = random.choice(self.get_unassigned_groups(assignments))

        # Generate chosen group's partitions
        domain, to_be_assigned_tiles = selected_group.generate_domain(assignments)
        # Order variables based on strategy
        if use_LCV:
            domain = selected_group.create_ordered_domain(domain, to_be_assigned_tiles, assignments)

        # Iterate over each partition, adding it to assignments and generating the restricted partition list for the affected groups;
        # Then check whether a group's partition list becomes empty. If so, remove assignment.
        for partition in domain:
            new_assignment = {}
            j = 0
            for tile in to_be_assigned_tiles:
                new_assignment[tile] = partition[j]
                j += 1

            # time.sleep(2)
            # Utils.print_board(Utils.update_board(assignments, new_assignment))
            # print(f'Previous assignments -> {assignments}')
            # print(f'New assignment -> {new_assignment}')
            # print("--------------------------------------------------------")
            if not self.check_current_consistency(assignments, new_assignment):
                continue
            assignments.update(new_assignment)
            result = self.solve(assignments, use_MCV, use_LCV)
            if result != -1:
                return result

            for key in new_assignment:
                assignments.pop(key)
        return -1


def main():
    try:
        selected_puzzle = sample_kakuro_puzzles.puzzles[sys.argv[1]]
    except:
        print("Puzzle not found.")
        return

    game_board, board_display_matrix = Kakuro.create_board_from_string(selected_puzzle[0], selected_puzzle[1])
    Kakuro.STARTING_BOARD = board_display_matrix

    use_MCV = False
    use_LCV = False
    if sys.argv[2] == 'mcv':
        use_MCV = True
    if sys.argv[3] == 'lcv':
        use_LCV = True
    os.system("cls")
    print("\nPuzzle to solve:")
    Utils.print_board(board_display_matrix)
    print("\n\nSolving...\n")
    start_time = time.perf_counter_ns()
    final_assignments = game_board.solve({}, use_MCV, use_LCV)
    end_time = time.perf_counter_ns()

    if final_assignments == -1:
        print("No solution found.")
        return
    else:
        print("A solution was found.")
        elapsed_time = end_time - start_time
        print(f'Time to solve: {(int(elapsed_time) / 1000.0):.0f} \u00B5s | {(int(elapsed_time) / 1000000.0):.0f} ms\n')
    Utils.print_board(Utils.update_board(final_assignments))


if __name__ == '__main__':
    main()
