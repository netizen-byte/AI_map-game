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

        self.current = self.start    
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
