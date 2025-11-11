from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from webapp.models import users


class RegistrationForm(FlaskForm):
    fullname = StringField('Fullname', validators=[DataRequired(), Length(min=2, max=20)])
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=4, max=10)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=4, max=10), EqualTo('password')])
    authority = SelectField(label='Authority', choices = [('superuser','superuser'),('admin','admin'),('user','user'),('driver', 'driver'),('temp','temp')], default='user')
    submit = SubmitField('Create New User')

    def validate_authority(self, authority):
        print('authority check is:',authority.data)
        if authority.data not in ['superuser', 'admin', 'user', 'temp']:
            raise ValidationError('Must be superuser, admin, user, or temp')

    def validate_username(self, username):
        thisuser = users.query.filter_by(username=username.data).first()
        if thisuser:
            raise ValidationError('This username is taken.  Please choose another,')

    def validate_fullname(self, fullname):
        thisuser = users.query.filter_by(name=fullname.data).first()
        if thisuser:
            raise ValidationError('This user already has an account!!')

    def validate_email(self, email):
        thisuser = users.query.filter_by(email=email.data).first()
        if thisuser:
            raise ValidationError(f'This email is being used by {thisuser.name}')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators = [DataRequired(), Length(min=4, max=10)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')