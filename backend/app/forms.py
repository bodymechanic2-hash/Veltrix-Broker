"""WTForms definitions.

Every state-changing form is protected by Flask-WTF's CSRF token and validated
server-side. Client-side HTML validation is a convenience only.
"""
from decimal import Decimal, InvalidOperation

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class RegistrationForm(FlaskForm):
    name = StringField(
        "Full name", validators=[DataRequired(message="Please enter your name."), Length(max=120)]
    )
    email = StringField(
        "Email address",
        validators=[DataRequired(message="Please enter your email."), Email(message="Enter a valid email address."), Length(max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please choose a password."),
            Length(min=8, max=128, message="Password must be between 8 and 128 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(message="Please confirm your password."), EqualTo("password", message="Passwords must match.")],
    )
    agree = BooleanField("I understand this is a demo and agree to the demo terms.", validators=[DataRequired(message="You must accept the demo terms to continue.")])
    submit = SubmitField("Create demo account")


class LoginForm(FlaskForm):
    email = StringField(
        "Email address",
        validators=[DataRequired(message="Please enter your email."), Email(message="Enter a valid email address.")],
    )
    password = PasswordField("Password", validators=[DataRequired(message="Please enter your password.")])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class TradeForm(FlaskForm):
    instrument_id = HiddenField("Instrument", validators=[DataRequired()])
    submission_id = HiddenField("Submission token")
    side = SelectField("Side", choices=[("buy", "Buy"), ("sell", "Sell")], validators=[DataRequired()])
    quantity = StringField("Quantity", validators=[DataRequired(message="Enter a quantity.")])
    submit = SubmitField("Review simulation")

    def validate_quantity(self, field):
        try:
            value = Decimal(field.data.strip())
        except (InvalidOperation, AttributeError, ValueError):
            raise ValidationError("Quantity must be a number.")
        if not value.is_finite() or value <= 0:
            raise ValidationError("Quantity must be a positive, finite number.")
        if value > Decimal("1000000000"):
            raise ValidationError("Quantity is unrealistically large.")


class WatchlistForm(FlaskForm):
    instrument_id = HiddenField("Instrument", validators=[DataRequired()])
    submit = SubmitField("Toggle watchlist")


class SupportForm(FlaskForm):
    subject = StringField(
        "Subject", validators=[DataRequired(message="Please add a subject."), Length(min=3, max=160, message="Subject must be 3-160 characters.")]
    )
    message = TextAreaField(
        "Message", validators=[DataRequired(message="Please write a message."), Length(min=10, max=4000, message="Message must be 10-4000 characters.")]
    )
    submit = SubmitField("Submit demo request")


class AdminSupportForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[("open", "Open"), ("in_progress", "In progress"), ("resolved", "Resolved")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Update status")


class TopUpForm(FlaskForm):
    submission_id = HiddenField("Submission token")
    amount = DecimalField(
        "Amount",
        places=2,
        validators=[DataRequired(message="Enter an amount."), NumberRange(min=Decimal("1"), max=Decimal("100000"), message="Enter an amount between 1 and 100000.")],
    )
    submit = SubmitField("Add demo funds")


class ForgotPasswordForm(FlaskForm):
    email = StringField(
        "Email address", validators=[DataRequired(message="Please enter your email."), Email(message="Enter a valid email address.")]
    )
    submit = SubmitField("Request reset")
