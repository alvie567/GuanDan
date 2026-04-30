from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from .models import Room, Player
from . import db
import random
import string

views = Blueprint('views', __name__)


def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    error = None
    if request.method == 'POST':
        action = request.form.get('action')
        # Use first name as default nickname
        nickname = (request.form.get('nickname') or current_user.first_name).strip()

        if action == 'create':
            code = gen_code()
            while Room.query.filter_by(code=code).first():
                code = gen_code()
            room = Room(code=code)
            db.session.add(room)
            db.session.commit()
            return redirect(url_for('views.game', code=code, nickname=nickname))

        elif action == 'join':
            code = request.form.get('room_code', '').strip().upper()
            if not code:
                error = 'Please enter a room code.'
            else:
                room = Room.query.filter_by(code=code).first()
                if room:
                    players = Player.query.filter_by(room_id=room.id).all()
                    if len(players) >= 4:
                        error = 'Room is full (4/4 players).'
                        return render_template('home.html', user=current_user, error=error)
                return redirect(url_for('views.game', code=code, nickname=nickname))

    return render_template('home.html', user=current_user, error=error)


@views.route('/game/<code>')
@login_required
def game(code):
    nickname = request.args.get('nickname', current_user.first_name)
    return render_template('game.html', room_code=code.upper(), nickname=nickname)


@views.route('/debug')
def debug():
    try:
        rooms = Room.query.all()
        players = Player.query.all()
        out = '<h2>Rooms</h2><ul>'
        for r in rooms:
            out += f'<li>Code: {r.code}, ID: {r.id}</li>'
        out += '</ul><h2>Players</h2><ul>'
        for p in players:
            out += f'<li>{p.nickname} · {p.seat} · Room {p.room_id}</li>'
        out += '</ul>'
        return out
    except Exception as e:
        return f'<pre>{e}</pre>'
