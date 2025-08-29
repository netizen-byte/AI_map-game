from collections import deque

class Node:
    def __init__(self, name, hint="", trap=False):
        self.name = name
        self.doors = {}  # door_name -> (connected_node)
        self.hint = hint
        self.trap = trap

    def add_door(self, door_name, node):
        self.doors[door_name] = node

    def __repr__(self):
        return f"Node({self.name})"

class BFSGame:
    def __init__(self, nodes, start_name, goal_name):
        self.nodes = nodes
        self.start = self.nodes[start_name]
        self.goal = self.nodes[goal_name]

        self.current = self.start
        self.path_history = [self.start]
        self.dead = False
        self.steps_taken = 0

    def breadth_first_search(self, start, goal):
        """Return shortest path (by edges) from start to goal."""
        queue = deque([(start, [])])  # (current_node, path)
        visited = set()

        while queue:
            current, path = queue.popleft()
            
            if current in visited:
                continue
            visited.add(current)
            
            new_path = path + [current]

            if current == goal:
                return new_path

            for door, neighbor in current.doors.items():
                if neighbor not in visited:
                    queue.append((neighbor, new_path))
        
        return []

    def get_current_options(self):
        """Return available doors with neighbor names."""
        options = []
        for door, neighbor in self.current.doors.items():
            options.append((door, neighbor.name, neighbor.hint))
        return options

    def move_to(self, door_name):
        if door_name not in self.current.doors:
            return False

        neighbor = self.current.doors[door_name]
        self.current = neighbor
        self.path_history.append(neighbor)
        
        # Check for trap after moving
        if self.current.trap:
            self.steps_taken += 0
            self.dead = True
            self.reset()
        else:
            self.dead = False
            self.steps_taken += 1

        return True

    def reset(self):
        self.current = self.start
        self.path_history = [self.start]
        self.dead = False

    def is_goal_reached(self):
        return self.current == self.goal
        
    def is_dead(self):
        return self.dead

    def get_shortest_path_to_goal(self):
        path = self.breadth_first_search(self.current, self.goal)
        return path