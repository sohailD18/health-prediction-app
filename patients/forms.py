import re
from datetime import date

from django import forms

from .models import Patient

# Letters, spaces, hyphens and apostrophes only, starting with a letter.
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z\s'\-]*$")

# A word made only of uppercase Roman numeral letters in a valid order (XI, III, IV...).
ROMAN_PATTERN = re.compile(r'^M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$')

# Exactly dd.mm.yyyy or dd/mm/yyyy (two-digit day and month, four-digit year).
DATE_PATTERN = re.compile(r'^\d{2}[./]\d{2}[./]\d{4}$')

MAX_AGE_YEARS = 120


class PatientForm(forms.ModelForm):
    # Accept both dd.mm.yyyy and dd/mm/yyyy. Impossible dates (e.g. 31.11.2001)
    # fail here automatically and show the "invalid" message below.
    date_of_birth = forms.DateField(
        input_formats=['%d.%m.%Y', '%d/%m/%Y'],
        widget=forms.DateInput(format='%d.%m.%Y', attrs={'placeholder': 'dd.mm.yyyy'}),
        error_messages={
            'required': 'Date of birth is required.',
            'invalid': 'Enter a real date in dd.mm.yyyy format (for example 28.01.1960).',
        },
    )

    glucose = forms.FloatField(
        min_value=20, max_value=600,
        error_messages={
            'required': 'Glucose is required.',
            'invalid': 'Glucose must be a number.',
            'min_value': 'Glucose must be at least 20 mg/dL.',
            'max_value': 'Glucose must be at most 600 mg/dL.',
        },
    )
    haemoglobin = forms.FloatField(
        min_value=3, max_value=25,
        error_messages={
            'required': 'Haemoglobin is required.',
            'invalid': 'Haemoglobin must be a number.',
            'min_value': 'Haemoglobin must be at least 3 g/dL.',
            'max_value': 'Haemoglobin must be at most 25 g/dL.',
        },
    )
    cholesterol = forms.FloatField(
        min_value=50, max_value=600,
        error_messages={
            'required': 'Cholesterol is required.',
            'invalid': 'Cholesterol must be a number.',
            'min_value': 'Cholesterol must be at least 50 mg/dL.',
            'max_value': 'Cholesterol must be at most 600 mg/dL.',
        },
    )

    class Meta:
        model = Patient
        # "remarks" is not typed by the user; the AI fills it in the view.
        fields = ['full_name', 'date_of_birth', 'email',
                  'glucose', 'haemoglobin', 'cholesterol']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bootstrap styling for every input
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # Show 232 instead of 232.0 when editing (13.5 stays 13.5)
        for name in ('glucose', 'haemoglobin', 'cholesterol'):
            value = self.initial.get(name)
            if value is not None:
                self.initial[name] = f'{value:g}'

    def clean_full_name(self):
        name = ' '.join(self.cleaned_data['full_name'].split())  # tidy extra spaces
        if len(name) < 2:
            raise forms.ValidationError('Name must be at least 2 characters.')
        if not NAME_PATTERN.match(name):
            raise forms.ValidationError(
                'Name may contain only letters, spaces, hyphens and apostrophes.')
        # Reject Roman numerals such as XI or III (uppercase words of 2+ letters)
        for word in name.split():
            if len(word) >= 2 and ROMAN_PATTERN.match(word):
                raise forms.ValidationError(
                    f'Name cannot contain Roman numerals (found "{word}").')
        return name

    def clean_date_of_birth(self):
        # Runs only if the date was already parsed as a real date.
        raw = self.data.get('date_of_birth', '').strip()
        if not DATE_PATTERN.match(raw):
            raise forms.ValidationError(
                'Use the format dd.mm.yyyy (for example 28.01.1960).')
        dob = self.cleaned_data['date_of_birth']
        if dob > date.today():
            raise forms.ValidationError('Date of birth cannot be in the future.')
        if dob.year < date.today().year - MAX_AGE_YEARS:
            raise forms.ValidationError(
                f'Date of birth cannot be more than {MAX_AGE_YEARS} years ago.')
        return dob   # a clean_ method must always return the value

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        # exclude self.instance so editing a record does not clash with itself
        duplicates = Patient.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError('A patient with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get('full_name')
        dob = cleaned.get('date_of_birth')
        # Only run this check when the email was not already flagged as a duplicate,
        # so the user does not see two messages for the same problem.
        if name and dob and 'email' not in self.errors:
            duplicates = Patient.objects.filter(full_name__iexact=name, date_of_birth=dob)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError(
                    'A patient with this name and date of birth already exists.')
        return cleaned