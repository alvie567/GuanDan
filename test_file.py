import sys
sys.path.insert(0, '.')
from website.guandan_logic import classify, beats

PASS = 0
FAIL = 0

def parse(cards_str):
    cards = []
    for s in cards_str.split():
        if s in ('BJ', 'RJ'):
            cards.append({'v': s, 's': ''})
        else:
            cards.append({'v': s[:-1], 's': s[-1]})
    return cards

def check(desc, cards_str, level, expected_type):
    global PASS, FAIL
    cards = parse(cards_str)
    result = classify(cards, level)
    got = result[0] if result else None
    ok = got == expected_type
    status = '✓' if ok else '✗'
    if not ok:
        print(f"{status} FAIL: {desc}")
        print(f"       cards={cards_str} level={level}")
        print(f"       expected={expected_type} got={got} full={result}")
        FAIL += 1
    else:
        print(f"{status} PASS: {desc}")
        PASS += 1

def check_rank(desc, cards_str, level, expected_type, expected_rank):
    global PASS, FAIL
    cards = parse(cards_str)
    result = classify(cards, level)
    got_type = result[0] if result else None
    got_rank = result[1] if result else None
    ok = got_type == expected_type and got_rank == expected_rank
    status = '✓' if ok else '✗'
    if not ok:
        print(f"{status} FAIL: {desc}")
        print(f"       cards={cards_str} level={level}")
        print(f"       expected=({expected_type}, rank={expected_rank}) got=({got_type}, rank={got_rank})")
        FAIL += 1
    else:
        print(f"{status} PASS: {desc}")
        PASS += 1

def check_beats(desc, new_str, pile_str, level, expected):
    global PASS, FAIL
    new = parse(new_str)
    pile = parse(pile_str)
    result = beats(new, pile, level)
    ok = result == expected
    status = '✓' if ok else '✗'
    if not ok:
        print(f"{status} FAIL: {desc}")
        print(f"       new={new_str} pile={pile_str} level={level}")
        print(f"       expected={expected} got={result}")
        nc = classify(new, level)
        pc = classify(pile, level)
        print(f"       new_combo={nc} pile_combo={pc}")
        FAIL += 1
    else:
        print(f"{status} PASS: {desc}")
        PASS += 1

def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

# ============================================================
section("SINGLES — basic")
# ============================================================
check("single 2",               "2S",               "3", "single")
check("single 3",               "3S",               "2", "single")
check("single 5",               "5D",               "2", "single")
check("single 10",              "10H",              "2", "single")
check("single J",               "JC",               "2", "single")
check("single Q",               "QS",               "2", "single")
check("single K",               "KH",               "2", "single")
check("single A",               "AS",               "2", "single")
check("single BJ",              "BJ",               "2", "single")
check("single RJ",              "RJ",               "2", "single")

section("SINGLES — level cards")
check("single level (non-heart)","6S",              "6", "single")
check("single level heart=wild", "6H",              "6", "single")
check("single level 10",        "10C",              "10","single")
check("single level A",         "AS",               "A", "single")
check("single level 2",         "2D",               "2", "single")

section("SINGLES — rank ordering")
check_rank("2 rank < 3",        "2S",               "5", "single", 0)
check_rank("3 rank=1",          "3S",               "5", "single", 1)
check_rank("A rank=12",         "AS",               "5", "single", 12)
check_rank("level card rank=20","5S",               "5", "single", 20)
check_rank("BJ rank=25",        "BJ",               "5", "single", 25)
check_rank("RJ rank=30",        "RJ",               "5", "single", 30)

# ============================================================
section("PAIRS — basic")
# ============================================================
check("pair 2s",                "2S 2H",            "3", "pair")
check("pair 3s",                "3S 3H",            "2", "pair")
check("pair 5s",                "5D 5C",            "2", "pair")
check("pair 9s",                "9S 9H",            "2", "pair")
check("pair 10s",               "10S 10H",          "2", "pair")
check("pair Js",                "JS JH",            "2", "pair")
check("pair Qs",                "QS QH",            "2", "pair")
check("pair Ks",                "KS KH",            "2", "pair")
check("pair As",                "AS AH",            "2", "pair")
check("pair BJs",               "BJ BJ",            "2", "pair")
check("pair RJs",               "RJ RJ",            "2", "pair")

section("PAIRS — with wilds")
check("wild+3",                 "6H 3S",            "6", "pair")
check("wild+A",                 "6H AS",            "6", "pair")
check("wild+K",                 "6H KS",            "6", "pair")
check("wild+level non-heart",   "6H 6S",            "6", "pair")
check("2 wilds = pair",         "6H 6H",            "6", "pair")

section("PAIRS — level cards")
check("pair level non-heart",   "6S 6C",            "6", "pair")
check("pair level mixed suits", "6S 6D",            "6", "pair")

section("PAIRS — invalid")
check("mismatch 7 8",           "7S 8S",            "2", None)
check("mismatch A K",           "AS KS",            "2", None)
check("BJ+RJ not pair",         "BJ RJ",            "2", None)
check("BJ+normal not pair",     "BJ 5S",            "2", None)

# ============================================================
section("TRIPLES — basic")
# ============================================================
check("triple 3s",              "3S 3H 3C",         "2", "triple")
check("triple 7s",              "7S 7H 7C",         "2", "triple")
check("triple 10s",             "10S 10H 10C",      "2", "triple")
check("triple Qs",              "QS QH QC",         "2", "triple")
check("triple As",              "AS AH AC",         "2", "triple")
check("triple 2s",              "2S 2H 2C",         "3", "triple")

section("TRIPLES — with wilds")
check("1 wild + pair 5s",       "6H 5S 5H",         "6", "triple")
check("1 wild + pair Ks",       "6H KS KH",         "6", "triple")
check("1 wild + pair As",       "6H AS AH",         "6", "triple")
check("2 wilds + single Q",     "6H 6H QS",         "6", "triple")
check("2 wilds + single 3",     "6H 6H 3S",         "6", "triple")
check("2 wilds + level non-heart","6H 6H 6S",       "6", "triple")

section("TRIPLES — invalid")
check("3 diff cards",           "3S 4H 5D",         "2", None)
check("pair+extra",             "7S 7H 8C",         "2", None)
check("joker in triple",        "BJ 7S 7H",         "2", None)
check("joker in triple 2",      "RJ 7S 7H",         "2", None)

# ============================================================
section("FULL HOUSE — basic")
# ============================================================
check("FH 3s+2s",               "3C 3H 3S 2C 2D",  "6", "fullhouse")
check("FH Qs+7s",               "QS QH QC 7S 7H",  "2", "fullhouse")
check("FH As+Ks",               "AS AH AC KS KH",  "2", "fullhouse")
check("FH 2s+3s",               "2S 2H 2C 3S 3H",  "4", "fullhouse")
check("FH 10s+9s",              "10S 10H 10C 9S 9H","2","fullhouse")
check("FH Js+5s",               "JS JH JC 5S 5H",  "2", "fullhouse")

section("FULL HOUSE — with wilds")
check("FH wild fills triple",   "6H QS QH 7S 7H",  "6", "fullhouse")
check("FH wild fills pair",     "6H QS QH QC 7S",  "6", "fullhouse")
check("FH 2 wilds",             "6H 6H QS 7S 7H",  "6", "fullhouse")
check("FH 2 wilds v2",          "6H 6H QS QH 7S",  "6", "fullhouse")

section("FULL HOUSE — invalid")
check("5 diff cards",           "3S 4H 5D 6C 7S",  "2", "straight")  # straight not FH
check("4+1",                    "QS QH QC QD 7S",  "2", None)  # bomb not FH
check("all same",               "7S 7H 7C 7D 7S",  "2", "bomb")  # bomb

# ============================================================
section("STRAIGHTS — basic")
# ============================================================
check("straight 3-7",           "3S 4H 5D 6C 7S",  "2", "straight")
check("straight 4-8",           "4S 5H 6D 7C 8S",  "2", "straight")
check("straight 5-9",           "5S 6H 7D 8C 9S",  "2", "straight")
check("straight 6-10",          "6S 7H 8D 9C 10S", "2", "straight")
check("straight 7-J",           "7S 8H 9D 10C JS", "2", "straight")
check("straight 8-Q",           "8S 9H 10D JC QS", "2", "straight")
check("straight 9-K",           "9S 10H JD QC KS", "2", "straight")
check("straight 10-A",          "10S JH QD KC AS", "2", "straight")
check("straight mixed suits",   "3S 4H 5H 6D 7C",  "2", "straight")
check("A wrap around",          "AS 2H 3D 4C 5S",  "9", "straight")

section("STRAIGHTS — with wilds")
check("wild fills gap 8-Q",     "6H 8S 9H 10D JC", "6", "straight")
check("wild extends low",       "6H 5S 6S 7H 8D",  "6", "straight") # wait level=6, 6S is level not wild
check("wild at top 7-J",        "6H 7S 8H 9D 10C", "6", "straight")
check("2 wilds in straight",    "6H 6H 5S 6S 7H",  "6", "straight") # 2 wilds+3 fixed

section("STRAIGHTS — invalid")
check("gap too big",            "3S 4H 5D 7C 8S",  "2", None)
check("duplicate in straight",  "3S 3H 5D 6C 7S",  "2", None)
check("4 cards only",           "3S 4H 5D 6C",     "2", None)
check("6 cards",                "3S 4H 5D 6C 7S 8H","2",None)

# ============================================================
section("STRAIGHT FLUSH — basic")
# ============================================================
check("SF 3-7 spades",          "3S 4S 5S 6S 7S",  "2", "straightflush")
check("SF 3-7 hearts",          "3H 4H 5H 6H 7H",  "9", "straightflush")
check("SF 3-7 diamonds",        "3D 4D 5D 6D 7D",  "2", "straightflush")
check("SF 3-7 clubs",           "3C 4C 5C 6C 7C",  "2", "straightflush")
check("SF 10-A spades",         "10S JS QS KS AS",  "2", "straightflush")
check("SF 8-Q hearts",          "8H 9H 10H JH QH",  "2","straightflush")

section("STRAIGHT FLUSH — with wilds")
check("SF wild fills gap",      "6H 3S 4S 5S 7S",  "6", "straightflush")
check("SF wild extends",        "6H 4S 5S 6S 7S",  "6", "straightflush")

section("STRAIGHT FLUSH — invalid")
check("SF mixed suits",         "3S 4H 5S 6S 7S",  "2", "straight")
check("SF non-consecutive",     "3S 4S 5S 7S 8S",  "2", None)

# ============================================================
section("BOMBS — 4-card")
# ============================================================
check("4-bomb 3s",              "3S 3H 3D 3C",     "2", "bomb")
check("4-bomb 5s",              "5S 5H 5D 5C",     "2", "bomb")
check("4-bomb 9s",              "9S 9H 9D 9C",     "2", "bomb")
check("4-bomb As",              "AS AH AD AC",      "2", "bomb")
check("4-bomb Ks",              "KS KH KD KC",      "2", "bomb")
check("4-bomb level cards",     "6S 6H 6D 6C",     "6", "bomb")
check("4-bomb with 1 wild",     "6H 5S 5H 5D",     "6", "bomb")
check("4-bomb with 2 wilds",    "6H 6H 5S 5H",     "6", "bomb")
check("4-bomb with 3 wilds",    "6H 6H 6H 5S",     "6", "bomb")

section("BOMBS — 5-card")
check("5-bomb 7s",              "7S 7H 7D 7C 7S",  "2", "bomb")
check("5-bomb with 1 wild",     "6H AS AH AD AC",  "6", "bomb")
check("5-bomb with 2 wilds",    "6H 6H AS AH AD",  "6", "bomb")

section("BOMBS — 6,7,8 card")
check("6-bomb As",              "AS AH AD AC AS AH","2","bomb")
check("7-bomb with wilds",      "6H 6H 6H AS AH AD AC","6","bomb")
check("8-bomb with wilds",      "6H 6H 6H 6H AS AH AD AC","6","bomb")

section("JOKER BOMB")
check("BJBJRJRJ",               "BJ BJ RJ RJ",     "2", "jokerbomb")

# ============================================================
section("TUBE — 3 consecutive pairs")
# ============================================================
check("tube 3-4-5",             "3S 3H 4S 4H 5S 5H","2","tube")
check("tube 4-5-6",             "4S 4H 5S 5H 6S 6H","2","tube")
check("tube 7-8-9",             "7S 7H 8S 8H 9S 9H","2","tube")
check("tube 10-J-Q",            "10S 10H JS JH QS QH","2","tube")
check("tube Q-K-A",             "QS QH KS KH AS AH","2","tube")
check("tube with 1 wild",       "6H 4S 4H 5S 5H 6S","6","tube")
check("tube with 2 wilds",      "6H 6H 4S 4H 5S 5H","6","tube")

section("TUBE — invalid")
check("non-consecutive pairs",  "3S 3H 5S 5H 7S 7H","2",None)
check("3 pairs same rank",      "7S 7H 7D 7C 7S 7H","2","bomb")

# ============================================================
section("PLATE — 2 consecutive triples")
# ============================================================
check("plate 3-4",              "3S 3H 3C 4S 4H 4C","2","plate")
check("plate 7-8",              "7S 7H 7C 8S 8H 8C","2","plate")
check("plate Q-K",              "QS QH QC KS KH KC","2","plate")
check("plate with 1 wild",      "6H 7S 7H 8S 8H 8C","6","plate")
check("plate with 2 wilds",     "6H 6H 7S 7H 8S 8H","6","plate") # Needs check - 2 wilds for 2 missing in triples

section("PLATE — invalid")
check("non-consecutive triples","3S 3H 3C 5S 5H 5C","2",None)
check("plate A-? invalid",      "AS AH AC 3S 3H 3C","2",None)

# ============================================================
section("BEATS — singles")
# ============================================================
check_beats("K beats Q",        "KS","QS",          "2", True)
check_beats("Q loses to K",     "QS","KS",          "2", False)
check_beats("A beats K",        "AS","KS",          "2", True)
check_beats("level beats A",    "6S","AS",           "6", True)
check_beats("BJ beats level",   "BJ","6S",           "6", True)
check_beats("RJ beats BJ",      "RJ","BJ",           "2", True)
check_beats("same rank tie",    "KS","KH",           "2", False)

section("BEATS — pairs")
check_beats("pair 9s beats 8s", "9S 9H","8S 8H",    "2", True)
check_beats("pair As beats Ks", "AS AH","KS KH",    "2", True)
check_beats("wild pair beats A pair","6H KS","AS AH","6", False)
check_beats("level pair beats A pair","6S 6H","AS AH","6",True)
check_beats("diff type fails",  "7S 7H","5S",        "2", False)

section("BEATS — bombs vs non-bombs")
check_beats("4-bomb beats single",  "AS AH AD AC","KS",        "2", True)
check_beats("4-bomb beats pair",    "AS AH AD AC","KS KH",     "2", True)
check_beats("4-bomb beats triple",  "AS AH AD AC","KS KH KC",  "2", True)
check_beats("4-bomb beats straight","AS AH AD AC","3S 4H 5D 6C 7S","2",True)
check_beats("4-bomb beats FH",      "AS AH AD AC","QS QH QC 7S 7H","2",True)
check_beats("single cant beat bomb","KS","AS AH AD AC","2",False)

section("BEATS — bomb priority")
check_beats("5-bomb beats 4-bomb",  "7S 7H 7D 7C 7S","AS AH AD AC",     "2", True)
check_beats("SF beats 5-bomb",      "3S 4S 5S 6S 7S","AS AH AD AC AS",   "2", True)
check_beats("6-bomb beats SF",      "AS AH AD AC AS AH","3S 4S 5S 6S 7S","2", True)
check_beats("7-bomb beats 6-bomb",  "AS AH AD AC AS AH AD","AS AH AD AC AS AH","2",True)
check_beats("8-bomb beats 7-bomb",  "AS AH AD AC AS AH AD AC","AS AH AD AC AS AH AD","2",True)
check_beats("joker beats 8-bomb",   "BJ RJ BJ RJ","AS AH AD AC AS AH AD AC","2",True)
check_beats("4-bomb loses to 5-bomb","AS AH AD AC","7S 7H 7D 7C 7S",   "2", False)
check_beats("5-bomb loses to SF",   "AS AH AD AC AS","3S 4S 5S 6S 7S",  "2", False)
check_beats("SF loses to 6-bomb",   "3S 4S 5S 6S 7S","AS AH AD AC AS AH","2",False)

section("BEATS — same type rank comparison")
check_beats("higher 4-bomb wins",   "AS AH AD AC","KS KH KD KC",      "2", True)
check_beats("higher SF wins",       "4S 5S 6S 7S 8S","3S 4S 5S 6S 7S","2", True)
check_beats("higher straight wins", "4S 5H 6D 7C 8S","3S 4H 5D 6C 7S","2", True)
check_beats("higher pair wins",     "9S 9H","8S 8H",                  "2", True)
check_beats("lower pair loses",     "8S 8H","9S 9H",                  "2", False)

section("BEATS — empty pile (any legal play wins)")
check_beats("single on empty",      "5S","",         "2", True)
check_beats("pair on empty",        "7S 7H","",      "2", True)
check_beats("bomb on empty",        "AS AH AD AC","","2", True)

# ============================================================
section("EDGE CASES")
# ============================================================
check("empty hand",             "",                 "2", None)
check("wild is not joker sub",  "6H BJ",            "6", None)
check("RJ+BJ not pair",         "RJ BJ",            "2", None)
check("level card in SF",       "3S 4S 6S 7S 8S",  "6", None) # 6 is level, not consecutive
check("duplicate straight card","3S 3H 4D 5C 6S",  "2", None)

print()
print("=" * 60)
print(f"FINAL RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
print("=" * 60)