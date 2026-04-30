from . import db
from flask_login import UserMixin
import json


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(6), unique=True, nullable=False)
    game_state = db.Column(db.Text, default='{}')
    host_sid = db.Column(db.String(100))
    players = db.relationship('Player', backref='room', lazy=True)

    def get_state(self):
        return json.loads(self.game_state or '{}')

    def set_state(self, state):
        self.game_state = json.dumps(state)


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100))
    nickname = db.Column(db.String(50))
    seat = db.Column(db.String(10))
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'))
