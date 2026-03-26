from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from webapp.models import users, BotClient


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
        if authority.data not in ['superuser', 'admin', 'user', 'temp', 'driver']:
            raise ValidationError('Must be superuser, admin, user, driver, or temp')

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



class BotClientForm(FlaskForm):
    name = StringField('Bot Name', validators=[DataRequired(), Length(min=2, max=50)])
    client_id = StringField('Client ID', validators=[DataRequired(), Length(min=4, max=50)])
    client_secret = PasswordField('Client Secret', validators=[DataRequired(), Length(min=12, max=100)])
    confirm_secret = PasswordField(
        'Confirm Secret',
        validators=[DataRequired(), EqualTo('client_secret')]
    )
    platform = SelectField(
        'Platform',
        choices=[
            ('telegram', 'telegram'),
            ('openclaw', 'openclaw'),
            ('internal', 'internal'),
            ('other', 'other')
        ],
        default='telegram'
    )
    authority = SelectField(
        'Authority',
        choices=[
            ('bot', 'bot'),
            ('bot_readonly', 'bot_readonly'),
            ('bot_admin', 'bot_admin')
        ],
        default='bot'
    )
    scopes = StringField(
        'Scopes',
        validators=[DataRequired(), Length(min=1, max=255)]
    )
    active = BooleanField('Active', default=True)
    submit = SubmitField('Create New Bot Client')

    def validate_client_id(self, client_id):
        thisbot = BotClient.query.filter_by(client_id=client_id.data).first()
        if thisbot:
            raise ValidationError('This client_id is already in use. Please choose another.')

    def validate_name(self, name):
        thisbot = BotClient.query.filter_by(name=name.data).first()
        if thisbot:
            raise ValidationError('A bot with this name already exists.')