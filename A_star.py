from UCS import ucs_new
import heapq
import itertools
import random

# Use the same Node class as before
class Node:
    def __init__(self, name, danger_cost, trap=False):
        self.name = name
        self.doors = {}
        self.danger_cost = danger_cost
        self.trap = trap

    def add_door(self, door_name, node, cost):
        self.doors[door_name] = (node, cost)

    def __repr__(self):
        return f"Node({self.name}, {self.danger_cost}, trap={self.trap})"


# A* using UCS upper bound as heuristic
class A_star_game:
    def __init__(self, nodes, start_name, goal_name):
        self.nodes = nodes
        self.start = nodes[start_name]
        self.goal = nodes[goal_name]

        # # Precompute UCS costs from every node to the goal
        # self.ucs_costs = {}
        # for node_name, node in nodes.items():
        #     ucs_game = ucs_new.UCSGame(nodes, start_name=node_name, goal_name=self.goal.name)
        #     cost, _ = ucs_game.uniform_cost_search(ucs_game.start, ucs_game.goal)
        #     # Make heuristic slightly smaller than real UCS cost for diversity
        #     self.ucs_costs[node_name] = max(0, cost - random.randint(0, 2))

    def heuristic_biased(self, node):
        self.ucs_costs = {}
        for node_name, node in nodes.items():
            ucs_game = ucs_new.UCSGame(nodes, start_name=node_name, goal_name=self.goal.name)
            cost, _ = ucs_game.uniform_cost_search(ucs_game.start, ucs_game.goal)
            # Make heuristic slightly smaller than real UCS cost for diversity
            self.ucs_costs[node_name] = max(0, cost - random.randint(0, 0))        
        return self.ucs_costs.get(node.name, float('inf'))
    
    def heuristic_true(self, node):
        return self.ucs_costs.get(node.name, float('inf'))

    def search(self):
        frontier = []
        counter = itertools.count()
        heapq.heappush(frontier, (0 + self.heuristic_biased(self.start), next(counter), self.start, 0, []))
        visited = set()

        while frontier:
            f_score, _, current, g_score, path = heapq.heappop(frontier)
            if current.name in visited:
                continue
            visited.add(current.name)
            new_path = path + [current]

            if current == self.goal:
                return g_score, new_path

            for neighbor, edge_cost in current.doors.values():
                new_g = g_score + neighbor.danger_cost + edge_cost
                f = new_g + self.heuristic_biased(neighbor)
                heapq.heappush(frontier, (f, next(counter), neighbor, new_g, new_path))

        return float('inf'), []


# ---------------- Example Graph ----------------

# Nodes
A = ucs_new.Node("A", danger_cost=1)
B = ucs_new.Node("B", danger_cost=5)
C = ucs_new.Node("C", danger_cost=2)
D = ucs_new.Node("D", danger_cost=2)
E = ucs_new.Node("E", danger_cost=1)
F = ucs_new.Node("F", danger_cost=3)

# Edges (some have higher edge cost, some lower)
A.add_door("to_B", B, 2)
A.add_door("to_C", C, 1)
B.add_door("to_D", D, 2)
C.add_door("to_D", D, 5)  # longer but cheaper danger
D.add_door("to_E", E, 1)
B.add_door("to_F", F, 1)
F.add_door("to_E", E, 1)

nodes = {"A": A, "B": B, "C": C, "D": D, "E": E, "F": F}

# ---------------- Run UCS ----------------
ucs_game = ucs_new.UCSGame(nodes, start_name="A", goal_name="E")
ucs_cost, ucs_path = ucs_game.uniform_cost_search(ucs_game.start, ucs_game.goal)
print("=== UCS Path ===")
print("Cost:", ucs_cost)
print("Path:", [n.name for n in ucs_path])

# ---------------- Run A* ----------------
a_star_game = A_star_game(nodes, start_name="A", goal_name="E")
a_cost, a_path = a_star_game.search()
print("\n=== A* Path ===")
print("Cost:", a_cost)
print("Path:", [n.name for n in a_path])
