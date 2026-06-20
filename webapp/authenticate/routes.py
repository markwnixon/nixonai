from flask import render_template, flash, redirect, url_for, session, Blueprint, request
#from webapp import db, bcrypt

from webapp.extensions import db, bcrypt
#from webapp import app, bcrypt

from webapp.models import users, BotClient
from webapp.authenticate.forms import RegistrationForm, LoginForm, BotClientForm
from flask_login import login_user, current_user, logout_user, login_required
from webapp.CCC_system_setup import companydata, scac
from webapp.financial_mfa import (
    clear_financial_mfa_session,
    get_mfa_settings,
    mark_financial_mfa_verified,
    send_financial_mfa_email,
    verify_financial_email_code,
)
import datetime
cmpdata = companydata()

authenticate = Blueprint('authenticate',__name__)

# Dray trucking authentication route
@authenticate.route('/dray-login', methods=['GET', 'POST'])
def dray_login():
    form = LoginForm()

    if form.validate_on_submit():
        thisuser = users.query.filter_by(username=form.username.data).first()

        if thisuser is not None:
            passcheck = bcrypt.check_password_hash(thisuser.password, form.password.data)

            if passcheck:
                session['logged_in'] = True
                session['username'] = thisuser.username
                session['authority'] = thisuser.authority
                clear_financial_mfa_session()
                login_user(thisuser, remember=form.remember.data)

                return redirect(url_for('main.EasyStart'))
            else:
                flash('Passwords do not match', 'danger')
        else:
            flash('Username not found', 'danger')

    return render_template(
        'authenticate/dray_login.html',   # 👈 NEW TEMPLATE
        cmpdata=cmpdata,
        scac=scac,
        form=form
    )

# User login
@authenticate.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        thisuser = users.query.filter_by(username=form.username.data).first()
        if thisuser is not None:
            passhash = thisuser.password
            #Commented out....only needed for startup if no superuser in database
            #hashed_pw = bcrypt.generate_password_hash(thisuser.password).decode('utf-8')
            #print(hashed_pw)
            passcheck = bcrypt.check_password_hash(passhash, form.password.data)

            if passcheck:
                session['logged_in'] = True
                session['username'] = thisuser.username
                session['authority'] = thisuser.authority
                clear_financial_mfa_session()
                login_user(thisuser, remember=form.remember.data)
                return redirect(url_for('main.EasyStart'))
            else:
                flash('Passwords do not match', 'danger')
                return render_template('authenticate/login.html', cmpdata=cmpdata, scac=scac, form=form)
        else:
            flash('Username not found', 'danger')
    else:
        return render_template('authenticate/login.html', cmpdata=cmpdata, scac=scac, form=form)

# Logout
@authenticate.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('authenticate.login'))

@authenticate.route('/register', methods=['GET', 'POST'])
@login_required

def register():
    if session['authority'] == 'superuser':
        print('user is', session['username'])
        print('authority is', session['authority'])
        form = RegistrationForm()
        if form.validate_on_submit():
            flash(f'New User Created for {form.fullname.data}:', 'success')
            hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            input = users(name=form.fullname.data, email=form.email.data, username=form.username.data, password=hashed_pw, register_date=None, authority=form.authority.data)
            db.session.add(input)
            db.session.commit()
            return redirect(url_for('authenticate.login'))
        return render_template('authenticate/register.html', title='Register', form=form, cmpdata=cmpdata, scac=scac)
    else:
        flash(f'Do not have authority to register new users', 'danger')
        return redirect(url_for('main.EasyStart'))


@authenticate.route('/mfa/financial/settings', methods=['GET', 'POST'])
@login_required
def mfa_settings():
    if session.get('authority') != 'superuser':
        flash('Do not have authority to manage MFA settings', 'danger')
        return redirect(url_for('main.EasyStart'))

    settings = get_mfa_settings(scac)
    if request.method == 'POST':
        settings.financial_mfa_required = request.values.get('financial_mfa_required') == 'on'
        try:
            timeout_minutes = int(request.values.get('timeout_minutes') or 720)
        except:
            timeout_minutes = 720
        settings.timeout_minutes = max(15, min(timeout_minutes, 1440))
        settings.updated_by = current_user.username
        settings.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        clear_financial_mfa_session()
        flash('Financial MFA settings updated', 'success')
        return redirect(url_for('authenticate.mfa_settings'))

    return render_template(
        'authenticate/mfa_settings.html',
        cmpdata=cmpdata,
        scac=scac,
        settings=settings,
    )


@authenticate.route('/mfa/financial/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    next_url = request.values.get('next') or url_for('main.EasyStart')
    flash('Financial MFA uses the email address on your user account.', 'info')
    return redirect(url_for('authenticate.mfa_verify', next=next_url))


@authenticate.route('/mfa/financial/verify', methods=['GET', 'POST'])
@login_required
def mfa_verify():
    settings = get_mfa_settings(scac)
    next_url = request.values.get('next') or url_for('main.EasyStart')

    if request.method == 'POST':
        if request.values.get('resend_code') == '1':
            sent, message = send_financial_mfa_email(force=True)
            flash(message, 'success' if sent else 'danger')
            return redirect(url_for('authenticate.mfa_verify', next=next_url))

        code = request.values.get('code')
        if verify_financial_email_code(code):
            mark_financial_mfa_verified(settings)
            flash('Financial MFA verified', 'success')
            return redirect(next_url)
        flash('MFA code was not valid or has expired', 'danger')
    else:
        sent, message = send_financial_mfa_email()
        flash(message, 'success' if sent else 'danger')

    return render_template(
        'authenticate/mfa_verify.html',
        cmpdata=cmpdata,
        scac=scac,
        next_url=next_url,
    )


@authenticate.route('/register_bot', methods=['GET', 'POST'])
@login_required
def register_bot():
    if session['authority'] == 'superuser':
        print('user is', session['username'])
        print('authority is', session['authority'])

        form = BotClientForm()

        if form.validate_on_submit():
            flash(f'New Bot Client Created for {form.name.data}', 'success')

            hashed_secret = bcrypt.generate_password_hash(
                form.client_secret.data
            ).decode('utf-8')

            input_row = BotClient(
                name=form.name.data,
                client_id=form.client_id.data,
                client_secret=hashed_secret,
                register_date=None,
                authority=form.authority.data,
                active=form.active.data,
                platform=form.platform.data,
                scopes=form.scopes.data.strip()
            )

            db.session.add(input_row)
            db.session.commit()

            flash('Save the raw client secret now. It cannot be recovered later.', 'warning')
            return redirect(url_for('main.EasyStart'))

        return render_template(
            'authenticate/register_bot.html',
            title='Register Bot',
            form=form,
            cmpdata=cmpdata,
            scac=scac
        )
    else:
        flash('Do not have authority to register new bot clients', 'danger')
        return redirect(url_for('main.EasyStart'))
