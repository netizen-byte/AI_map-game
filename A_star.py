from UCS import ucs_new
import heapq
import itertools

# Use the same Node class as before
class Node:
    def __init__(self, name, danger_cost, trap=False, x=0, y=0, heuristic=0):
        self.name = name
        self.doors = {}
        self.danger_cost = danger_cost
        self.trap = trap
        self.x = x
        self.y = y
        self.heuristic = heuristic

    def add_door(self, door_name, node, cost):
        self.doors[door_name] = (node, cost)

    def __repr__(self):
        return f"Node({self.name}, x={self.x}, y={self.y}, heuristic={self.heuristic}, trap={self.trap})"


# A* using UCS upper bound as heuristic
class A_star_game:
    def __init__(self, nodes, start_name, goal_name):
        self.nodes = nodes
        self.start = nodes[start_name]
        self.goal = nodes[goal_name]
    
    # def heuristic_euclidian(self, node):
    #     for node in self.nodes.values():
    #         h = ((node.x - self.goal.x) ** 2 + (node.y - self.goal.y) ** 2) ** 0.5
    #         node.heuristic = round(h, 1)  # store in node

    def search(self):

        for node in self.nodes.values():
            h = ((node.x - self.goal.x) ** 2 + (node.y - self.goal.y) ** 2) ** 0.5
            node.heuristic = round(h, 1)  # store in node

        frontier = []
        counter = itertools.count()
        # use stored heuristic
        heapq.heappush(frontier, (0 + self.start.heuristic, next(counter), self.start, 0, []))
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
                f = new_g + neighbor.heuristic  # use precomputed heuristic
                heapq.heappush(frontier, (f, next(counter), neighbor, new_g, new_path))

        return float('inf'), []


# ---------------- Example Graph ----------------

# Nodes with coordinates (x, y)
A = Node("A", danger_cost=1, x=0, y=0)
B = Node("B", danger_cost=5, x=2, y=0)
C = Node("C", danger_cost=2, x=0, y=2)
D = Node("D", danger_cost=2, x=2, y=2)
E = Node("E", danger_cost=1, x=4, y=2)
F = Node("F", danger_cost=3, x=2, y=4)

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
for n in a_path:
    print(n)
