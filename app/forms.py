from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FloatField, SelectField, FileField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from flask_wtf.file import FileAllowed

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class GameForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    short_description = StringField('Short Description', validators=[DataRequired(), Length(max=200)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    image_file = FileField('Game Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only!')
    ])
    
    # Fitur stok
    stock = IntegerField('Stock Quantity', validators=[
        DataRequired(), 
        NumberRange(min=0, message='Stock cannot be negative')
    ], default=0)
    
    # Metode share game
    share_method = SelectField('Share Method', choices=[
        ('cloud_code', 'Cloud Code/Phone Code'),
        ('account', 'Account (Email & Password)')
    ], validators=[DataRequired()])
    
    cloud_code = StringField('Cloud/Phone Code', validators=[Optional()])
    account_email = StringField('Account Email', validators=[Optional(), Email()])
    account_password = StringField('Account Password', validators=[Optional()])
    
    category = StringField('Category', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Game')

class PaymentMethodForm(FlaskForm):
    name = StringField('Payment Name', validators=[DataRequired()])
    type = SelectField('Type', choices=[
        ('bank_transfer', 'Bank Transfer'),
        ('ewallet', 'E-Wallet'), 
        ('qris', 'QRIS')
    ], validators=[DataRequired()])
    account_number = StringField('Account Number', validators=[DataRequired()])
    account_name = StringField('Account Name', validators=[DataRequired()])
    qr_code_file = FileField('QR Code Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    instructions = TextAreaField('Instructions', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Payment Method')

class PaymentProofForm(FlaskForm):
    payment_method = SelectField('Payment Method', choices=[], validators=[DataRequired()])
    proof_image = FileField('Payment Proof', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf'], 'Images and PDF only!')
    ])
    submit = SubmitField('Place Order')

# ==================== TAMBAHAN FORM SETTINGS ====================

class AdminSettingsForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[Optional()])
    submit = SubmitField('Update Settings')