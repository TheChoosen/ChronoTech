from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, DateField, IntegerField
from wtforms.validators import DataRequired, Email, Length, Optional

class CustomerForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(max=255)])
    customer_type = SelectField('Type', choices=[('particulier', 'Particulier'), ('entreprise', 'Entreprise')], validators=[Optional()])
    company = StringField('Société', validators=[Optional(), Length(max=255)])
    siret = StringField('SIRET', validators=[Optional(), Length(max=14)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    status = SelectField('Statut', choices=[('actif', 'Actif'), ('inactif', 'Inactif')], validators=[Optional()])
    address = TextAreaField('Adresse', validators=[Optional(), Length(max=255)])
    postal_code = StringField('Code postal', validators=[Optional(), Length(max=10)])
    city = StringField('Ville', validators=[Optional(), Length(max=100)])
    country = StringField('Pays', validators=[Optional(), Length(max=100)])
    billing_address = TextAreaField('Adresse de facturation', validators=[Optional(), Length(max=255)])
    payment_terms = SelectField('Conditions de paiement', choices=[('30j', '30 jours'), ('60j', '60 jours'), ('comptant', 'Comptant')], validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    tax_number = StringField('Numéro de TVA', validators=[Optional(), Length(max=32)])
    preferred_contact_method = SelectField('Contact préféré', choices=[('email', 'Email'), ('phone', 'Téléphone')], validators=[Optional()])
    zone = StringField('Zone', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Ajouter')

class TechnicianForm(FlaskForm):
    name = StringField('Nom', validators=[DataRequired(), Length(max=255)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    specialty = StringField('Spécialité', validators=[Optional(), Length(max=100)])
    status = SelectField('Statut', choices=[('actif', 'Actif'), ('inactif', 'Inactif')], validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ajouter')

class WorkOrderForm(FlaskForm):
    title = StringField('Titre', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    customer_id = IntegerField('Client', validators=[DataRequired()])
    technician_id = IntegerField('Technicien', validators=[Optional()])
    status = SelectField('Statut', choices=[('en_attente', 'En attente'), ('en_cours', 'En cours'), ('termine', 'Terminé')], validators=[Optional()])
    due_date = DateField('Date d\'échéance', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ajouter')
