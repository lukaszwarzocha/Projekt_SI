def _a_star(self, start, goal, indest_walls, dest_walls_coords):
    # Heurystyka: odleglosc Euklidesowa
    def h(a, b):
        return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5
 
    queue = [(0, start)]
    came_from = {start: None}
    cost_so_far = {start: 0}
 
    while queue:
        _, curr = heapq.heappop(queue)
        if curr == goal:
            break
        for d in [(0,1),(0,-1),(1,0),(-1,0)]:
            nxt = (curr[0]+d[0], curr[1]+d[1])
            if not (0 <= nxt[0] < 20 and 0 <= nxt[1] < 15):
                continue
            if nxt in indest_walls:
                continue  # niezniszczalna - pomijamy
            step = 6 if nxt in dest_walls_coords else 1
            new_cost = cost_so_far[curr] + step
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                heapq.heappush(queue, (new_cost + h(nxt, goal), nxt))
                came_from[nxt] = curr
 
    # Odtwarzamy sciezke wstecz od celu do startu
    path, c = [], goal
    while c in came_from and c != start:
        path.append(c)
        c = came_from[c]
    return path[::-1]