import heapq
import itertools
import random

class Node:
    def __init__(self, name, danger_cost, trap=False):
        self.name = name
        self.doors = {}  # door_name -> (connected_node, cost)
        self.danger_cost = danger_cost
        self.trap = trap

    def add_door(self, door_name, node, cost):
        self.doors[door_name] = (node, cost)

    def __repr__(self):
        return f"Node({self.name, self.danger_cost, self.trap})"


class UCSGame:
    def __init__(self, nodes, start_name, goal_name):
        self.nodes = nodes
        self.start = self.nodes[start_name]
        self.goal = self.nodes[goal_name]

        self.current = self.start
        self.total_cost = 0
        self.dead = False
        self.path_history = [self.start]

    def uniform_cost_search(self, start, goal):
        frontier = []
        counter = itertools.count()
        # push (cost, tie_breaker, node, path)
        heapq.heappush(frontier, (0, next(counter), start, []))
        visited = set()

        while frontier:
            cost, _, current, path = heapq.heappop(frontier)
            if current.name in visited:
                continue
            visited.add(current.name)
            new_path = path + [current]

            if current.name == goal.name:
                return cost, new_path

            for neighbor, edge_cost in current.doors.values():

                total_cost = cost + neighbor.danger_cost + edge_cost
                heapq.heappush(frontier, (total_cost, next(counter), neighbor, new_path))

        return float("inf"), []

    def get_current_options(self):
        """Return available doors with neighbor, cost, and intuitive hint"""
        options = []
        for door, (neighbor, cost) in self.current.doors.items():
            hint = self.generate_hint(neighbor.danger_cost)
            options.append((door, neighbor.name, cost, hint))
        return options

    def generate_hint(self, danger_cost):
        """Intuitive hint based on danger cost (higher cost = riskier)"""
        if danger_cost >= 5:
            return "You are lack of aura, go farm more. This room is not for you"
        elif danger_cost >= 3:
            return "You aura is not on my level yet, be slightly careful"
        elif danger_cost >= 2:
            return "You are almost there, you mogged most of the people"
        else:
            return "Infinite aura, you are safe"
    
    def move_to(self, door_name):
        if door_name not in self.current.doors:
            return False

        neighbor, cost = self.current.doors[door_name]
        self.total_cost += neighbor.danger_cost + cost
        self.current = neighbor
        self.path_history.append(neighbor)

        if self.current.trap:
            self.dead = True
            self._reset_after_death()
        else:
            self.dead = False

        return True

    def _reset_after_death(self):
        self.current = self.start
        self.total_cost = 0
        self.path_history = [self.start]

    def is_goal_reached(self):
        return self.current == self.goal

    def get_least_cost_to_goal(self):
        cost, _ = self.uniform_cost_search(self.current, self.goal)
        return cost
    

# Sample dungeon setup
# Nodes: A, B, C, D, E
# Connections (doors) and costs:
# A -> B (2), C (4)
# B -> D (7)
# C -> D (1), E (3)
# D -> E (2)
# Danger costs: A=1, B=2, C=3, D=4, E=1
# Trap: D is a trap

# Create nodes
# A = Node("A", danger_cost=0)
# B = Node("B", danger_cost=2)
# C = Node("C", danger_cost=3)
# D = Node("D", danger_cost=4, trap=True)
# E = Node("E", danger_cost=0)

# # Add doors (neighbor node, edge cost)
# A.add_door("to_B", B, 2)
# A.add_door("to_C", C, 4)
# B.add_door("to_D", D, 7)
# B.add_door("to_E", E, 4)
# C.add_door("to_D", D, 3)
# C.add_door("to_E", E, 2)

# # Put all nodes in a dictionary
# nodes = {"A": A, "B": B, "C": C, "D": D, "E": E}

# # Initialize UCSGame
# game = UCSGame(nodes, start_name="A", goal_name="E")

# Test UCS from start to goal
# cost, path = game.uniform_cost_search(game.start, game.goal)
# print("UCS Total Cost:", cost)
# print("UCS Path:", [node.name for node in path])

# # Test current options from start
# options = game.get_current_options()
# print("\nCurrent Options from A:")
# for option in options:
#     door, neighbor_name, cost, hint = option
#     print(f"Door: {door}, Leads to: {neighbor_name}, Edge Cost: {cost}, Hint: {hint}")

# # Move through a path
# print("\nMoving through A -> C -> E")
# game.move_to("to_C")
# game.move_to("to_E")
# print("Current Room:", game.current.name)
# print("Total Cost so far:", game.total_cost)
# print("Path History:", [node.name for node in game.path_history])

#Testing with A*

# Nodes
# A = Node("A", danger_cost=1)
# B = Node("B", danger_cost=2)
# C = Node("C", danger_cost=2)
# D = Node("D", danger_cost=3)
# E = Node("E", danger_cost=1)

# # Connect doors (edge_costs are varied)
# A.add_door("to_B", B, cost=1)
# A.add_door("to_C", C, cost=2)
# B.add_door("to_D", D, cost=5)
# C.add_door("to_D", D, cost=1)
# D.add_door("to_E", E, cost=1)

# nodes = {"A": A, "B": B, "C": C, "D": D, "E": E}
# ucs_game = UCSGame(nodes, start_name="A", goal_name="E")
# ucs_cost, ucs_path = ucs_game.uniform_cost_search(ucs_game.start, ucs_game.goal)

# print("=== UCS Path ===")
# print("Cost:", ucs_cost)
# print("Path:", [n.name for n in ucs_path])
