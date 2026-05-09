"""
Guandan card validation logic.
All card objects: {'v': str, 's': str}  (s in S/H/D/C/'')

Card rank: 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < level cards < BJ < RJ
Heart level card = universal wild (cannot sub for jokers)

Bomb priority: 4-card < 5-card < straight flush < 6-card < 7-card < 8-card < joker bomb
"""

# 2 is lowest normal card
VALS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
VAL_RANK = {v: i for i, v in enumerate(VALS)}  # 2=0, 3=1 ... A=12

def card_rank(card, level):
    v = card['v']
    if v == 'RJ': return 30
    if v == 'BJ': return 25
    if v == level: return 20  # level cards (all suits) outrank A
    return VAL_RANK.get(v, -1)

def is_wild(card, level):
    """Heart level card = universal wild (cannot substitute jokers)."""
    return card['v'] == level and card['s'] == 'H'

def is_level_card(card, level):
    return card['v'] == level

def group_by_rank_without_level(cards, level):
    """Group non-wild cards by effective rank."""
    groups = {}
    for c in cards:
        if is_wild(c, level):
            continue
        groups.setdefault(VAL_RANK[c['v']], []).append(c)
    return groups

def group_by_rank(cards, level):
    """Group non-wild cards by effective rank."""
    groups = {}
    for c in cards:
        if is_wild(c, level):
            continue
        r = card_rank(c, level)
        groups.setdefault(r, []).append(c)
    return groups

def classify(cards, level):
    """
    Returns (combo_type, rank_value, length) or None if illegal.
    
    Bomb priority encoded in rank_value:
      joker bomb: 9999
      8-card bomb: 8000 + rank
      7-card bomb: 7000 + rank
      straight flush: 6000 + start_rank  (beats 6-card bomb of same size? no — SF beats 6-card)
      Actually per rules: 4 < 5 < SF < 6 < 7 < 8 < joker
      We encode this in beats() logic, not rank_value.
    """
    n = len(cards)
    if n == 0:
        return None

    # Joker bomb: exactly 4 jokers
    jokers = [c for c in cards if c['v'] in ('BJ', 'RJ')]
    non_jokers = [c for c in cards if c['v'] not in ('BJ', 'RJ')]
    if len(jokers) == 4 and n == 4:
        return ('jokerbomb', 9999, 4)

    wilds = [c for c in non_jokers if is_wild(c, level)]
    non_wilds = [c for c in non_jokers if not is_wild(c, level)]
    wild_count = len(wilds)

    # All wilds → treat as level-card group
    if wild_count == n:
        if n == 1: return ('single', 100, 1)
        if n == 2: return ('pair', 100, 2)
        return None

    groups = group_by_rank(non_wilds, level)
    ranks_sorted = sorted(groups.keys())

    # --- Single ---
    if n == 1:
        return ('single', card_rank(cards[0], level), 1)

    # --- Pair ---
    if n == 2:
        if len(jokers) == 2:
            if jokers[0] == jokers[1]:
                return ('pair', card_rank(jokers[0], level), 2)
            else:
                return None
        elif len(jokers) == 1:
            return None
        else:
            if wild_count == 1:
                return ('pair', card_rank(non_wilds[0], level), 2)
            elif len(ranks_sorted) == 1 and len(groups[ranks_sorted[0]]) == 2:
                return ('pair', ranks_sorted[0], 2)
        return None

    # --- Triple ---
    if n == 3:
        if len(jokers) > 0:
            return None
        if wild_count == 2:
            return ('triple', card_rank(non_wilds[0], level), 3)
        if wild_count == 1:
            if len(ranks_sorted) == 1 and len(groups[ranks_sorted[0]]) == 2:
                return ('triple', ranks_sorted[0], 3)
            return None
        if len(ranks_sorted) == 1 and len(groups[ranks_sorted[0]]) == 3:
            return ('triple', ranks_sorted[0], 3)
        return None

    # --- 4-bomb ---
    if n == 4:
        if len(jokers) > 0:
            return None
        return(_try_bomb_n(non_wilds, wild_count, level, n))

    # --- 5-card combos ---
    if n == 5:
        if len(jokers) == 0 or len(jokers) == 2:
            r = _try_fullhouse(non_wilds, wild_count, jokers, level)
            if r: return r
        if len(jokers) > 0:
            return None
        r = _try_straightflush(non_wilds, wild_count)
        if r: return r
        r = _try_straight(non_wilds, wild_count, False)
        if r: return r
        r = _try_bomb_n(non_wilds, wild_count, level, 5)
        if r: return r
        return None

    if len(jokers) > 0:
        return None

    # --- 6-card combos ---
    if n == 6:
        groups = group_by_rank(non_wilds, level)
        ranks_sorted = sorted(groups.keys())
        if wild_count == 2 and len(ranks_sorted) == 2 and (ranks_sorted[1]-ranks_sorted[0] == 1 or ranks_sorted[1]-ranks_sorted[0] == 12) and len(groups[ranks_sorted[0]]) == 2 and len(groups[ranks_sorted[1]]) == 2:
            if ranks_sorted[0] == 0 and ranks_sorted[1] == 12:
                return ("tuplate", -1, 6)
            return ("tuplate", ranks_sorted[0], 6)
        r = _try_tube(non_wilds, wild_count, level)
        if r: return r
        r = _try_plate(non_wilds, wild_count, level)
        if r: return r
        r = _try_bomb_n(non_wilds, wild_count, level, 6)
        if r: return r
        return None

    # --- 7 or 8 card bombs ---
    if n == 8 or n == 7:
        r = _try_bomb_n(non_wilds, wild_count, level, n)
        if r: return r
        return None

    return None


def _try_bomb_n(non_wilds, wild_count, level, n):
    """All n cards same rank (wilds fill)."""
    groups = group_by_rank(non_wilds, level)
    ranks_sorted = list(groups.keys())
    if len(ranks_sorted) == 1:
        rank = ranks_sorted[0]
        if len(groups[rank]) + wild_count == n:
            return ('bomb', n * 100 + rank, n)
    return None


def _try_fullhouse(non_wilds, wild_count, jokers, level):
    """Triple + pair, wilds can fill either."""
    groups = group_by_rank(non_wilds, level)
    ranks_sorted = sorted(groups.keys())

    if len(jokers) == 2:
        if jokers[0] != jokers[1]:
            return None
        if len(ranks_sorted) != 1:
            return None
        return ('fullhouse', ranks_sorted[0], 5)

    if len(ranks_sorted) > 2:
        return None

    if (len(groups[ranks_sorted[0]]) > 3) or (len(ranks_sorted) == 2 and len(groups[ranks_sorted[1]]) > 3):
        return None
    
    if len(ranks_sorted) == 1:
        if len(groups[ranks_sorted[0]])!=3:
            return None
        return ('fullhouse', ranks_sorted[0], 5)

    if len(groups[ranks_sorted[1]]) == 3 or (len(groups[ranks_sorted[1]]) == 2 and wild_count > 0) or (len(groups[ranks_sorted[1]]) == 1 and wild_count == 2):
        return ('fullhouse', ranks_sorted[1], 5)
    else:
        return ('fullhouse', ranks_sorted[0], 5)


def _try_straightflush(non_wilds, wild_count):
    """5 consecutive same-suit cards, wilds fill gaps (wild doesn't provide suit)."""
    suit = non_wilds[0]['s']
    if not all(c['s'] == suit for c in non_wilds) or suit == '':
        return None
    return _try_straight(non_wilds, wild_count, True)


def _try_straight(non_wilds, wild_count, boo):
    base_vals = sorted(VAL_RANK.get(c['v'], -1) for c in non_wilds)
    # Try all 5-runs that can accommodate the fixed cards
    lo = max(0, base_vals[0] - wild_count)
    hi = base_vals[0]
    if len(set(base_vals)) != len(base_vals):
        return None
    for start in range(hi, lo-1, -1):
        run = list(range(start, start + 5))
        if run[-1] > 12: continue  # A=12 max
        needed = [v for v in run if v not in base_vals]
        dups = len([v for v in base_vals if v not in run])
        if len(needed) == wild_count and dups == 0:
            if boo:
                return ('straightflush', start, 5)
            else:
                return ('straight', start, 5)
    run = [0,1,2,3,12]
    needed = [v for v in run if v not in base_vals]
    dups = len([v for v in base_vals if v not in run])
    if len(needed) == wild_count and dups == 0:
        if boo:
            return ('straightflush', -1, 5)
        else:
            return ('straight', -1, 5)   
    return None


def _try_tube(non_wilds, wild_count, level):
    """3 consecutive pairs."""
    groups = group_by_rank_without_level(non_wilds, level)
    for start in range(10, -1, -1):
        run = [start, start+1, start+2]
        needed = sum(max(0, 2 - len(groups.get(r, []))) for r in run)
        extra = sum(max(0, len(groups.get(r, [])) - 2) for r in run)
        if needed == wild_count and extra == 0:
            return ('tube', start, 6)
    run = [0,1,12]
    needed = sum(max(0, 2 - len(groups.get(r, []))) for r in run)
    extra = sum(max(0, len(groups.get(r, [])) - 2) for r in run)
    if needed == wild_count and extra == 0:
        return ('tube', -1, 6)
    return None


def _try_plate(non_wilds, wild_count, level):
    """2 consecutive triples."""
    groups = group_by_rank_without_level(non_wilds, level)
    for start in range(11, -1, -1):
        run = [start, start+1]
        needed = sum(max(0, 3 - len(groups.get(r, []))) for r in run)
        extra = sum(max(0, len(groups.get(r, [])) - 3) for r in run)
        if needed == wild_count and extra == 0:
            return ('plate', start, 6)
    run = [0,12]
    needed = sum(max(0, 3 - len(groups.get(r, []))) for r in run)
    extra = sum(max(0, len(groups.get(r, [])) - 3) for r in run)
    if needed == wild_count and extra == 0:
        return ('plate', -1, 6)
    return None


BOMB_SIZE_PRIORITY = {4: 1, 5: 2, 6: 4, 7: 5, 8: 6}
# straight flush beats 6-card bomb → SF priority = 3
def beats(new_cards, current_combo, level):
    new_combo = classify(new_cards, level)
    if new_combo is None:
        return False
    nt, nv, nl = new_combo
    if current_combo is None:
        return True

    cur_combo = tuple(current_combo)

    ct, cv, cl = cur_combo

    # Joker bomb beats everything
    if nt == 'jokerbomb': return True
    if ct == 'jokerbomb': return False

    # Determine bomb priority scores
    def bomb_priority(t, l):
        if t == 'straightflush': return 3
        if t == 'bomb': return BOMB_SIZE_PRIORITY.get(l, 0)
        return 0  # not a bomb

    n_is_bomb = nt in ('bomb', 'straightflush')
    c_is_bomb = ct in ('bomb', 'straightflush')

    if n_is_bomb and not c_is_bomb:
        return True
    if c_is_bomb and not n_is_bomb:
        return False

    if n_is_bomb and c_is_bomb:
        np = bomb_priority(nt, nl)
        cp = bomb_priority(ct, cl)
        if np != cp:
            return np > cp
        # Same priority (same type and size): compare rank
        if nt == ct and nl == cl and nv != cv:
            return nv > cv
        return False

    # Non-bomb vs non-bomb: must be same type and same length
    if nt == "tuplate" and (ct == "plate" or ct == "tube"):
        if ct == "plate":
            return nv > cv
        else:
            if cv < 10:
                return nv > cv
            else:
                return False
        
    if nt != ct or nl != cl:
        return False
    if nv == cv:
        return False
    return nv > cv
