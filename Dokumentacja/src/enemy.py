
def _minimax(bx, by, px, py, indest_fs, dest_fs, cost_acc,
             depth, alpha, beta, maxi, powerups=None):
    if depth == 0:
        return _eval(bx, by, px, py, indest_fs, powerups, cost_acc)
 
    if maxi:  # Tura bota (MAX)
        best = -INF
        for d in DIRS:
            nx, ny = bx + d[0]*STEP, by + d[1]*STEP
            c = _move_cost(nx, ny, indest_fs, dest_fs)
            if c == INF:
                continue
            val = _minimax(nx, ny, px, py, indest_fs, dest_fs,
                           cost_acc + c, depth-1, alpha, beta, False, powerups)
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break  # PRZYCINANIE alfa-beta
        return best
    else:     # Tura gracza (MIN)
        if _player_can_shoot(bx, by, px, py, indest_fs):
            return _eval(...) - 60   # kara za strzał gracza
        best = INF
        for d in DIRS:
            nx, ny = px + d[0]*STEP, py + d[1]*STEP
            # (walidacja kafelka...)
            val = _minimax(bx, by, nx, ny, indest_fs, dest_fs,
                           cost_acc, depth-1, alpha, beta, True, powerups)
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best