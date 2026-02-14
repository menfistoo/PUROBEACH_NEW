"""
Authentication forms using Flask-WTF.
Provides login and profile editing forms with CSRF protection.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, Regexp


class LoginForm(FlaskForm):
    """Login form with username and password."""

    username = StringField('Usuario', validators=[
        DataRequired(message='El usuario es requerido')
    ])

    password = PasswordField('Contraseña', validators=[
        DataRequired(message='La contraseña es requerida')
    ])

    remember_me = BooleanField('Recordarme')


class ProfileForm(FlaskForm):
    """Profile editing form."""

    email = StringField('Correo Electrónico', validators=[
        DataRequired(message='El correo es requerido'),
        Email(message='Formato de correo inválido')
    ])

    full_name = StringField('Nombre Completo', validators=[
        Optional(),
        Length(max=200)
    ])

    theme_preference = SelectField('Tema', choices=[
        ('light', 'Claro'),
        ('dark', 'Oscuro')
    ])


class ChangePasswordForm(FlaskForm):
    """Password change form."""

    current_password = PasswordField('Contraseña Actual', validators=[
        DataRequired(message='La contraseña actual es requerida')
    ])

    new_password = PasswordField('Nueva Contraseña', validators=[
        DataRequired(message='La nueva contraseña es requerida'),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres'),
        Regexp(r'(?=.*[A-Z])', message='Debe contener al menos una mayúscula'),
        Regexp(r'(?=.*[a-z])', message='Debe contener al menos una minúscula'),
        Regexp(r'(?=.*\d)', message='Debe contener al menos un número'),
    ])

    confirm_password = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(message='Debe confirmar la contraseña'),
        EqualTo('new_password', message='Las contraseñas no coinciden')
    ])
