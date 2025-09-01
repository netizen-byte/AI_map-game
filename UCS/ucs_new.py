import heapq
import itertools

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
            return "You aura is not on my level yet, be sligyhtly careful"
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