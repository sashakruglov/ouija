
from datetime import date, timedelta

from wtforms import Form, DateField
from wtforms.validators import ValidationError


def validate_start_date(form, field):
    if field.data > date.today():
        raise ValidationError('Start date should not be greater than current date')

    if field.data >= form['end_date'].data:
        raise ValidationError('Start date should not be greater than end date')


def one_week_ago():
    return date.today() - timedelta(days=8)


class DatepickerForm(Form):

    start_date = DateField('Start date', default=one_week_ago, validators=[validate_start_date])
    end_date = DateField('End date', default=date.today())
