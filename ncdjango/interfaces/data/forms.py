from django import forms
from ncdjango.interfaces.arcgis.form_fields import SrField


class PointForm(forms.Form):
    x = forms.FloatField()
    y = forms.FloatField()
    projection = SrField()