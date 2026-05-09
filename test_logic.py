import sys
sys.path.insert(0, '.')
from website.guandan_logic import classify, beats

def c(cards_str, level='2'):
    """Parse shorthand like 'QS QH 2H' into cards and classify."""
    cards = []
    for s in cards_str.split():
        if s in ('BJ', 'RJ'):
            cards.append({'v': s, 's': ''})
        else:
            cards.append({'v': s[:-1], 's': s[-1]})
    result = classify(cards, level)
    print(f"classify({cards_str}, level={level}) → {result}")
    return result

def b(new_str, pile_str, level='2'):
    """Test if new beats pile."""
    def parse(s):
        cards = []
        for x in s.split():
            if x in ('BJ','RJ'):
                cards.append({'v': x, 's': ''})
            else:
                cards.append({'v': x[:-1], 's': x[-1]})
        return cards
    new = parse(new_str)
    pile = parse(pile_str)
    nc = classify(new, level)
    pc = classify(pile, level)
    result = beats(new, pile, level)
    print(f"beats({new_str} vs {pile_str}, level={level})")
    print(f"  new={nc}  pile={pc}  → {result}")
    return result

# ===== YOUR TESTS HERE =====
c('6H QS QH QC 7S', level='6')