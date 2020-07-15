from flask import render_template, flash, redirect, url_for, session, Blueprint
from webapp import db, bcrypt
from webapp.models import users
from webapp.authenticate.forms import RegistrationForm, LoginForm
from flask_login import login_user, current_user, logout_user, login_required
from webapp.CCC_system_setup import companydata, scac
cmpdata = companydata()

authenticate = Blueprint('authenticate',__name__)

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
                login_user(thisuser, remember=form.remember.data)
                return redirect(url_for('EasyStart'))
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
        return redirect(url_for('EasyStart'))