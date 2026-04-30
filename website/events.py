from flask import request
from flask_login import current_user
from flask_socketio import emit, join_room
from .models import Room, Player
from . import db, socketio
from .guandan_logic import classify, beats, VAL_RANK
import random

SEATS = ['bottom', 'left', 'top', 'right']
SEAT_LABELS = {'bottom': 'South', 'left': 'West', 'top': 'North', 'right': 'East'}
SUITS = ['S', 'H', 'D', 'C']
VALS = ['3','4','5','6','7','8','9','10','J','Q','K','A','2']
LEVELS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']


def build_deck():
    single = [{'v': v, 's': s} for s in SUITS for v in VALS]
    single += [{'v': 'BJ', 's': ''}, {'v': 'RJ', 's': ''}]
    deck = single + single  # two decks = 108 cards
    random.shuffle(deck)
    return deck


def deal(deck):
    # 108 cards / 4 players = 27 each
    return {
        'bottom': deck[0:27],
        'left':   deck[27:54],
        'top':    deck[54:81],
        'right':  deck[81:108],
    }


def _get_room_players(room_id):
    return Player.query.filter_by(room_id=room_id).all()


def _broadcast_lobby(code, room):
    players = _get_room_players(room.id)
    state = room.get_state()
    roster = [{'seat': p.seat, 'nickname': p.nickname, 'session_id': p.session_id} for p in players]
    is_host_map = {p.session_id: (p.session_id == room.host_sid) for p in players}
    emit('lobby_update', {
        'players': roster,
        'count': len(players),
        'settings': state.get('settings', _default_settings()),
        'host_sid': room.host_sid,
    }, to=code)


def _default_settings():
    return {
        'phase': 'lobby',       # lobby | pregame | playing
        'teams': {
            'A': ['bottom', 'top'],
            'B': ['left', 'right'],
        },
        'levels': {'A': '2', 'B': '2'},
        'last_placements': [],  # e.g. ['bottom','left','top','right'] = finish order
    }


@socketio.on('join_game')
def on_join(data):
    try:
        code = data.get('code', '').upper()
        nickname = (data.get('nickname') or 'Player').strip()
        sid = request.sid

        room = Room.query.filter_by(code=code).first()
        if not room:
            room = Room(code=code)
            state = {'settings': _default_settings()}
            room.set_state(state)
            db.session.add(room)
            db.session.commit()

        all_players = _get_room_players(room.id)

        # Reconnect check
        existing = next((p for p in all_players if p.session_id == sid), None)
        if existing:
            join_room(code)
            _broadcast_lobby(code, room)
            # Resend game state if playing
            state = room.get_state()
            if state.get('settings', {}).get('phase') == 'playing':
                _send_game_state_to(existing, room, state)
            return

        taken_seats = [p.seat for p in all_players]
        available = [s for s in SEATS if s not in taken_seats]
        if not available:
            emit('error', {'msg': 'Room is full (4/4)'})
            return

        seat = available[0]
        is_first = len(all_players) == 0
        player = Player(session_id=sid, nickname=nickname, seat=seat, room_id=room.id)
        db.session.add(player)

        if is_first:
            room.host_sid = sid

        # Save nickname to user account if it changed
        if current_user.is_authenticated and current_user.first_name != nickname:
            current_user.first_name = nickname

        db.session.commit()
        join_room(code)
        _broadcast_lobby(code, room)

    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})


@socketio.on('disconnect')
def on_disconnect():
    try:
        sid = request.sid
        player = Player.query.filter_by(session_id=sid).first()
        if player:
            room = Room.query.get(player.room_id)
            code = room.code if room else None
            seat = player.seat
            nickname = player.nickname
            was_host = (room and room.host_sid == sid)
            db.session.delete(player)
            db.session.commit()
            if code and room:
                # Transfer host if host left
                if was_host:
                    remaining = _get_room_players(room.id)
                    if remaining:
                        room.host_sid = remaining[0].session_id
                        db.session.commit()
                emit('player_left', {'seat': seat, 'nickname': nickname}, to=code)
                _broadcast_lobby(code, room)
    except Exception as e:
        db.session.rollback()


@socketio.on('update_settings')
def on_update_settings(data):
    """Host updates teams, levels, or placements in pregame."""
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        room = Room.query.filter_by(code=code).first()
        if not room or room.host_sid != sid:
            emit('error', {'msg': 'Only the host can change settings'})
            return

        state = room.get_state()
        settings = state.get('settings', _default_settings())

        if 'teams' in data:
            settings['teams'] = data['teams']
        if 'levels' in data:
            # Validate levels
            lv = data['levels']
            if lv.get('A') in LEVELS and lv.get('B') in LEVELS:
                settings['levels'] = lv
        if 'last_placements' in data:
            settings['last_placements'] = data['last_placements']

        state['settings'] = settings
        room.set_state(state)
        db.session.commit()
        # Don't broadcast lobby — clients stay on pregame screen
        emit('settings_updated', {'settings': settings}, to=code)

    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})


@socketio.on('host_start_game')
def on_host_start(data):
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        room = Room.query.filter_by(code=code).first()
        if not room:
            return
        if room.host_sid != sid:
            emit('error', {'msg': 'Only the host can start the game'})
            return
        players = _get_room_players(room.id)
        if len(players) < 2:
            emit('error', {'msg': 'Need at least 2 players to start'})
            return
        _start_game(room)
    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})


@socketio.on('play_cards')
def on_play(data):
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        cards = data.get('cards', [])

        player = Player.query.filter_by(session_id=sid).first()
        if not player:
            return
        room = Room.query.filter_by(code=code).first()
        if not room:
            return

        state = room.get_state()
        settings = state.get('settings', _default_settings())
        if settings.get('phase') != 'playing':
            return
        if state.get('active_seat') != player.seat:
            emit('error', {'msg': "It's not your turn"})
            return

        # Determine current level for this player's team
        level = _level_for_seat(player.seat, settings)
        current_pile = state.get('pile', [])
        last_seat = state.get('last_play_seat')

        # If this player owns the current pile (everyone else passed), any legal play
        if last_seat == player.seat:
            current_pile = []

        if not beats(cards, current_pile, level):
            combo = classify(cards, level)
            if combo is None:
                emit('error', {'msg': 'Invalid combination'})
            else:
                emit('error', {'msg': "Doesn't beat the current play"})
            return

        # Remove cards from hand
        hand = state['hands'].get(player.seat, [])
        played_ids = [c['v'] + c['s'] for c in cards]
        new_hand = []
        temp_played = list(played_ids)
        for c in hand:
            cid = c['v'] + c['s']
            if cid in temp_played:
                temp_played.remove(cid)
            else:
                new_hand.append(c)
        state['hands'][player.seat] = new_hand
        state['pile'] = cards
        state['last_play'] = {'seat': player.seat, 'cards': cards, 'combo': classify(cards, level)[0] if classify(cards, level) else 'unknown'}
        state['last_play_seat'] = player.seat
        state['passes'] = 0

        # Check if player finished
        if len(new_hand) == 0:
            finished = state.get('finished', [])
            finished.append(player.seat)
            state['finished'] = finished
            if len(finished) >= 3:
                # Round over
                state = _resolve_round(state, settings, room)
                room.set_state(state)
                db.session.commit()
                _broadcast_game_state(room, code)
                tributes = state.get('pending_tributes', [])
                if tributes:
                    # Broadcast game state so receivers see their new card
                    _broadcast_game_state(room, code)
                    emit('tribute_phase', {
                        'tributes': tributes,
                        'result': state.get('round_result', {})
                    }, to=code)
                else:
                    emit('round_over', state.get('round_result', {}), to=code)
                return

        # Advance turn (skip finished players)
        state = _advance_turn(state, player.seat)
        room.set_state(state)
        db.session.commit()
        _broadcast_game_state(room, code)

    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})


@socketio.on('pass_turn')
def on_pass(data):
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        player = Player.query.filter_by(session_id=sid).first()
        if not player:
            return
        room = Room.query.filter_by(code=code).first()
        if not room:
            return

        state = room.get_state()
        if state.get('active_seat') != player.seat:
            return

        passes = state.get('passes', 0) + 1
        state['passes'] = passes

        # Count active (non-finished) players minus the last player who played
        active_count = sum(1 for s in SEATS if s not in state.get('finished', []))
        # If everyone else passed, last player who played leads again with new play
        if passes >= active_count - 1:
            state['passes'] = 0
            state['pile'] = []
            # Give lead back to last_play_seat
            last = state.get('last_play_seat')
            if last and last not in state.get('finished', []):
                state['active_seat'] = last
            else:
                state = _advance_turn(state, player.seat)
        else:
            state = _advance_turn(state, player.seat)

        room.set_state(state)
        db.session.commit()
        emit('player_passed', {'seat': player.seat, 'nickname': player.nickname}, to=code)
        _broadcast_game_state(room, code)

    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})


@socketio.on('new_round')
def on_new_round(data):
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        room = Room.query.filter_by(code=code).first()
        if not room or room.host_sid != sid:
            return
        _start_game(room)
    except Exception as e:
        db.session.rollback()

@socketio.on('tribute_return')
def on_tribute_return(data):
    """Receiver chooses a card to return to the giver."""
    try:
        sid = request.sid
        code = data.get('code', '').upper()
        card = data.get('card')  # {'v':..,'s':..}

        player = Player.query.filter_by(session_id=sid).first()
        if not player:
            return
        room = Room.query.filter_by(code=code).first()
        if not room:
            return

        state = room.get_state()
        settings = state.get('settings', {})
        level = settings.get('current_level', '2')
        tributes = state.get('pending_tributes', [])

        # Validate: find tribute where this player is receiver
        tribute = next((t for t in tributes if t['receiver'] == player.seat), None)
        if not tribute:
            emit('error', {'msg': 'No tribute to return'})
            return

        # Validate return card: must be ≤10 and not the level card
        RETURNABLE_VALS = ['3','4','5','6','7','8','9','10']
        if card['v'] not in RETURNABLE_VALS or card['v'] == level:
            emit('error', {'msg': f'Return card must be ≤10 and not the level card ({level})'})
            return

        # Check card is in receiver's hand
        hand = state['hands'].get(player.seat, [])
        card_in_hand = next((c for c in hand if c['v'] == card['v'] and c['s'] == card['s']), None)
        if not card_in_hand:
            emit('error', {'msg': 'Card not in hand'})
            return

        # Execute exchange: give tribute card to receiver, return card to giver
        giver_hand = state['hands'].get(tribute['giver'], [])
        # Remove tribute card from giver
        tc = tribute['card']
        giver_hand = [c for c in giver_hand if not (c['v'] == tc['v'] and c['s'] == tc['s'])]
        # Add tribute card to receiver
        hand.append(tc)
        # Remove return card from receiver
        hand = [c for c in hand if not (c['v'] == card['v'] and c['s'] == card['s'])]
        # Add return card to giver
        giver_hand.append(card)

        state['hands'][tribute['giver']] = giver_hand
        state['hands'][player.seat] = hand

        # Mark this tribute as done
        state['pending_tributes'] = [t for t in tributes if t['receiver'] != player.seat]
        state['pending_returns'].append({'receiver': player.seat, 'giver': tribute['giver'], 'card': card})

        room.set_state(state)
        db.session.commit()

        # If all tributes resolved, emit round_over
        if not state['pending_tributes']:
            emit('round_over', state.get('round_result', {}), to=code)
        else:
            emit('tribute_update', {'remaining': len(state['pending_tributes'])}, to=code)

    except Exception as e:
        db.session.rollback()
        emit('error', {'msg': str(e)})

# ---------- helpers ----------

def _level_for_seat(seat, settings):
    # The active level is determined by the first-seat player's team
    first_seat = settings.get('first_seat', 'bottom')
    teams = settings.get('teams', {'A': ['bottom','top'], 'B': ['left','right']})
    levels = settings.get('levels', {'A': '2', 'B': '2'})
    for team, seats in teams.items():
        if first_seat in seats:
            return levels.get(team, '2')
    return '2'


def _advance_turn(state, current_seat):
    order = SEATS
    finished = state.get('finished', [])
    idx = order.index(current_seat)
    for _ in range(4):
        idx = (idx + 1) % 4
        next_seat = order[idx]
        if next_seat not in finished:
            state['active_seat'] = next_seat
            return state
    return state


def _resolve_round(state, settings, room):
    finished = state.get('finished', [])
    # Last remaining player is 4th
    remaining = [s for s in SEATS if s not in finished]
    if remaining:
        finished.append(remaining[0])
    state['finished'] = finished

    teams = settings.get('teams', {'A': ['bottom','top'], 'B': ['left','right']})
    levels = settings.get('levels', {'A': '2', 'B': '2'})

    first = finished[0]
    second = finished[1]

    # Determine first player's team
    first_team = next((t for t, seats in teams.items() if first in seats), 'A')
    second_team = next((t for t, seats in teams.items() if second in seats), 'B')

    if first_team == second_team:
        upgrade = 3
    elif second_team == first_team:
        upgrade = 2
    else:
        # 1st and 3rd
        third = finished[2]
        third_team = next((t for t, seats in teams.items() if third in seats), 'B')
        if first_team == third_team:
            upgrade = 2
        else:
            upgrade = 1

    # Apply upgrade
    LEVEL_ORDER = LEVELS
    winning_team = first_team
    cur_level = levels.get(winning_team, '2')
    cur_idx = LEVEL_ORDER.index(cur_level) if cur_level in LEVEL_ORDER else 0
    new_idx = min(cur_idx + upgrade, len(LEVEL_ORDER) - 1)
    new_level = LEVEL_ORDER[new_idx]
    levels[winning_team] = new_level

    settings['levels'] = levels
    settings['last_placements'] = finished

    # Check win condition
    won = False
    if new_level == 'A' and upgrade >= 1:
        fourth = finished[3]
        fourth_team = next((t for t, seats in teams.items() if fourth in seats), 'B')
        if fourth_team != winning_team:
            won = True

    state['round_result'] = {
        'placements': finished,
        'winning_team': winning_team,
        'upgrade': upgrade,
        'new_levels': levels,
        'game_won': won,
        'winner_team': winning_team if won else None,
    }
    settings['current_level'] = settings['levels'].get(winning_team, '2')
    state['settings'] = settings
    tributes = _compute_tribute(state, settings)
    state['pending_tributes'] = tributes
    state['pending_returns'] = []
    state['round_result']['tributes'] = tributes
    return state

def _start_game(room):
    state = room.get_state()
    settings = state.get('settings', _default_settings())
    settings['phase'] = 'playing'

    deck = build_deck()
    hands = deal(deck)

    # Determine who leads: last round's 1st place, or bottom by default
    last = settings.get('last_placements', [])
    first_seat = last[0] if last else 'bottom'
    settings['first_seat'] = first_seat
    # Skip if not in current players
    players = _get_room_players(room.id)
    player_seats = [p.seat for p in players]
    if first_seat not in player_seats:
        first_seat = player_seats[0] if player_seats else 'bottom'

    state = {
        'settings': settings,
        'hands': hands,
        'pile': [],
        'active_seat': first_seat,
        'last_play': None,
        'last_play_seat': None,
        'passes': 0,
        'finished': [],
    }
    room.set_state(state)
    db.session.commit()
    _broadcast_game_state(room, room.code)


def _send_game_state_to(player, room, state):
    seat = player.seat
    settings = state.get('settings', _default_settings())
    personal = {
        'phase': settings.get('phase', 'lobby'),
        'active_seat': state.get('active_seat'),
        'pile': state.get('pile', []),
        'last_play': state.get('last_play'),
        'your_seat': seat,
        'hand': state['hands'].get(seat, []),
        'hand_counts': {s: len(state['hands'].get(s, [])) for s in SEATS if s != seat},
        'finished': state.get('finished', []),
        'settings': settings,
        'level': _level_for_seat(seat, settings),
    }
    emit('game_state', personal, to=player.session_id)


def _broadcast_game_state(room, code):
    state = room.get_state()
    if not state or 'hands' not in state:
        return
    players = _get_room_players(room.id)
    for player in players:
        _send_game_state_to(player, room, state)

def _tribute_rank(card, level):
    """Rank for tribute purposes: RJ > BJ > level cards (not heart) > A > K..."""
    if card['v'] == 'RJ': return 100
    if card['v'] == 'BJ': return 99
    if card['v'] == level and card['s'] != 'H': return 98
    return VAL_RANK.get(card['v'], -1)

def _best_tribute_card(hand, level):
    """Return the highest tributeable card (excludes level-heart)."""
    eligible = [c for c in hand if not (c['v'] == level and c['s'] == 'H')]
    if not eligible:
        return None
    return max(eligible, key=lambda c: _tribute_rank(c, level))

def _compute_tribute(state, settings):
    """
    Returns list of tribute actions:
    [{'giver': seat, 'receiver': seat, 'card': card}, ...]
    Returns None if tribute is skipped (2 red jokers exemption).
    """
    finished = state['finished']
    teams = settings.get('teams', {'A':['bottom','top'],'B':['left','right']})
    level = settings.get('current_level', '2')

    p1, p2, p3, p4 = finished[0], finished[1], finished[2], finished[3]
    teamOf = lambda s: next((t for t,seats in teams.items() if s in seats), 'A')
    t1, t2 = teamOf(p1), teamOf(p2)

    # Who are the givers?
    if t1 == t2:
        # 双上: p3 and p4 give
        givers = [p3, p4]
    elif teamOf(p1) == teamOf(p3):
        # 1+3 same team: only p4 gives
        givers = [p4]
    else:
        # 1+4 same team or 1 alone: only p4 gives
        givers = [p4]

    # Check exemption: givers' team collectively holds 2 red jokers
    giving_team_seats = [s for s in SEATS if teamOf(s) == teamOf(givers[0])]
    rj_count = sum(
        1 for s in giving_team_seats
        for c in state['hands'].get(s, [])
        if c['v'] == 'RJ'
    )
    if rj_count >= 2:
        return []  # no tribute

    # Auto-pick best card from each giver
    tributes = []
    cards_given = []
    for giver in givers:
        hand = state['hands'].get(giver, [])
        card = _best_tribute_card(hand, level)
        if card:
            cards_given.append((giver, card))

    # Assign receivers
    if t1 == t2:
        # Sort by tribute rank descending: p1 gets higher, p2 gets lower
        cards_given.sort(key=lambda x: _tribute_rank(x[1], level), reverse=True)
        receivers = [p1, p2]
        # If equal value, p1 takes from p4, p2 takes from p3
        if len(cards_given) == 2 and _tribute_rank(cards_given[0][1], level) == _tribute_rank(cards_given[1][1], level):
            # Ensure p4→p1, p3→p2
            cards_given = sorted(cards_given, key=lambda x: x[0] == p4, reverse=True)
        for i, (giver, card) in enumerate(cards_given):
            tributes.append({'giver': giver, 'receiver': receivers[i], 'card': card})
    else:
        # Single tribute: p4 → p1
        for giver, card in cards_given:
            tributes.append({'giver': giver, 'receiver': p1, 'card': card})

    return tributes