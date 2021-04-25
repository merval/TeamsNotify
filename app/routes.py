from datetime import datetime, timedelta

import jwt
from flask import render_template, url_for, flash, redirect, request, session, make_response, jsonify, g
from flask_login import current_user, login_user, logout_user, login_required
from flask_mail import Message
from flask_restful import reqparse, abort
from flask_restplus import Api, Resource, fields
from app import app, db, mail
from app.forms import NotificationForm, RegistrationForm, LoginForm, ResetPasswordForm, RequestResetForm, \
    UserManagementForm, UpdateAccountForm
from app.models import Notifications, User


def generate_token(user):
    response = jwt.encode({'user': user.username, 'exp': datetime.utcnow() + timedelta(hours=24)},
                          app.config['SECRET_KEY'])
    return response


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            if user.disabled == 1:
                flash('This account has not been enabled! Please contact a site admin', 'danger')
                return redirect(url_for('home'))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            token = generate_token(user)
            setattr(user, 'token', token)
            db.session.commit()
            flash("Login Successful", 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    users_exist = User.query.all()
    if form.validate_on_submit():
        # Do any users exist? If not, make first user admin
        if len(users_exist) == 0:
            user = User(username=form.username.data, email=form.email.data, password=form.password.data, admin=1,
                        disabled=0)
        else:
            user = User(username=form.username.data, email=form.email.data, password=form.password.data, admin=0,
                        disabled=1)
            flash(f'Account created for {form.username.data}! An Administrator will enable your account', 'success')
        user.hash_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('register.html', title="Register", form=form)


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    user = User.query.filter_by(username=current_user.username).first()
    user_token = user.token.decode('utf-8')
    return render_template('account.html', title='Account', form=form, user_token=user_token)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/users", methods=['GET', 'POST'])
@login_required
def user_management():
    all_users = User.query.all()
    user = User.query.filter_by(username=current_user.username).first()
    if user.admin == 1:
        return render_template('accounts.html', all_users=all_users, legend='Account Management')
    flash('Only Admins can do that!', 'danger')
    return redirect(url_for('home'))


@app.route("/users/<int:user_id>/edit", methods=['GET', 'POST'])
@login_required
def single_user(user_id):
    edit_user = User.query.filter_by(id=user_id).first()
    if not edit_user:
        flash(f'That user does not exist!', 'warning')
        return redirect(url_for('home'))
    user = User.query.filter_by(username=current_user.username).first()
    if user.admin == 1:
        form = UserManagementForm()
        if form.validate_on_submit():
            user_id = form.user_id.data
            username = form.username.data
            email = form.email.data
            first_name = form.first_name.data
            last_name = form.last_name.data
            disabled = form.disabled.data
            admin = form.admin.data
            user_to_edit = User.query.filter_by(id=user_id).first()
            if form.delete.data:
                if user_to_edit.username == current_user.username:
                    flash(f"You can't delete yourself!", 'danger')
                    return redirect(url_for('user_management'))
                db.session.delete(user_to_edit)
                db.session.commit()
                flash(f'{username} has been deleted!', 'success')
                return redirect(url_for('user_management'))
            setattr(user_to_edit, 'username', username)
            setattr(user_to_edit, 'email', email)
            setattr(user_to_edit, 'firstname', first_name)
            setattr(user_to_edit, 'lastname', last_name)
            setattr(user_to_edit, 'disabled', disabled)
            setattr(user_to_edit, 'admin', admin)
            db.session.commit()
            flash('User updated', 'success')
            return redirect(url_for('user_management'))
        elif request.method == 'GET':
            form.username.data = edit_user.username
            form.email.data = edit_user.email
            form.user_id.data = edit_user.id
            form.first_name.data = edit_user.firstname
            form.last_name.data = edit_user.lastname
            form.disabled.data = edit_user.disabled
            form.admin.data = edit_user.admin
        return render_template('single_user.html', user=edit_user, form=form, legend=f'Edit {edit_user.username}')
    flash('Only Admins can do that!', 'danger')
    return redirect(url_for('home'))


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@tripwirelab.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.hash_password(form.password.data)
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


@app.route("/notifications", methods=['GET'])
def notifications_page():
    notification_settings = Notifications.query.all()
    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first()
    else:
        user = None
    return render_template('notifications.html', notification_settings=notification_settings, user=user)


@app.route("/notification/<int:notification_id>/delete", methods=['GET'])
def delete_notification(notification_id):
    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first()
        if user.admin != 1:
            flash('Access Denied', 'danger')
            return redirect(url_for('notifications_page'))
        notification = Notifications.query.filter_by(id=notification_id).first()
        db.session.delete(notification)
        db.session.commit()
        flash('Your team notification has been deleted!', 'success')
        return redirect(url_for('notifications_page'))
    else:
        flash('Access Denied', 'danger')
        return redirect(url_for('notifications_page'))


@app.route("/notifications/new", methods=['GET', 'POST'])
def new_notification():
    form = NotificationForm()
    if form.validate_on_submit():
        notification = Notifications()
        notification.team_name = form.team_name.data
        notification.teams_channel_url = form.teams_channel_url.data
        notification.enabled = form.enabled.data
        notification.updated = datetime.today().date()
        db.session.add(notification)
        db.session.commit()
        flash('Your team notification has been created!', 'success')
        return redirect(url_for('notifications_page'))
    return render_template('create_notification.html', title='Add New Notification',
                           form=form, legend='Add New Notification')


@app.route("/notifications/edit/<int:id>", methods=['GET', 'POST'])
def edit_notifications(id):
    notification = Notifications.query.get_or_404(id)
    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first()
        if user.admin != 1:
            flash('Access Denied', 'danger')
            return redirect(url_for('notifications_page'))
        form = NotificationForm()
        if form.validate_on_submit():
            notification.team_name = form.team_name.data
            notification.teams_channel_url = form.teams_channel_url.data
            notification.enabled = form.enabled.data
            notification.updated = datetime.today().date()
            db.session.commit()
            flash('Your team notification has been updated!', 'success')
            return redirect(url_for('notifications_page'))
        elif request.method == 'GET':
            form.team_name.data = notification.team_name
            form.teams_channel_url.data = notification.teams_channel_url
            form.enabled.data = notification.enabled

        return render_template('create_notification.html', title='Update Notification Settings',
                               form=form, legend='Update Notification Settings')
    flash('Only Administrators can manage notification settings', 'danger')
    return redirect(url_for('notifications_page'))
