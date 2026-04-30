from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            flash('Welcome back, ' + user.first_name + '!', 'success')
            return redirect(url_for('views.home'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html', user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('firstName', '').strip()
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
        elif len(email) < 4:
            flash('Email is too short.', 'error')
        elif len(first_name) < 2:
            flash('Name must be at least 2 characters.', 'error')
        elif password1 != password2:
            flash("Passwords don't match.", 'error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', 'error')
        else:
            user = User(
                email=email,
                first_name=first_name,
                password=generate_password_hash(password1, method='pbkdf2:sha256')
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created! Welcome, ' + first_name + '!', 'success')
            return redirect(url_for('views.home'))
    return render_template('sign_up.html', user=current_user)


@auth.route('/change-pass', methods=['GET', 'POST'])
@login_required
def change_pass():
    if request.method == 'POST':
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')
        if password1 != password2:
            flash("Passwords don't match.", 'error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', 'error')
        else:
            current_user.password = generate_password_hash(password1, method='pbkdf2:sha256')
            db.session.commit()
            flash('Password updated!', 'success')
            return redirect(url_for('views.home'))
    return render_template('change_pass.html', user=current_user)
