from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from webapp.models import People

custlist = []
data = People.query.filter(People.Ptype=='Trucking').order_by('Company').all()
for dat in data:
    customer = dat.Company
    custlist.append((customer,customer))

class TruckingFormNew(FlaskForm):
    order = StringField('Customer Reference Value', validators=[Length(min=4, max=20)])
    shipper = SelectField('Customer', choices=custlist)
    release = StringField('Release', validators=[Length(min=11, max=11)])
    container = StringField('Container', validators=[Length(min=11, max=11)])
    con_type = SelectField('Container Type')
    base_charge = StringField('Base Charge')
    loadat_previous = SelectField('Previous Load-At for Customer', choices = custlist)
    loadat = TextAreaField('Load At', render_kw={"rows": 4, "cols": 11})


    submit = SubmitField('Submit')
    cancel = SubmitField('Cancel')


    def validate_container(form, field):
        if 'M' not in field.data:
            raise ValidationError('Must contain an M')



