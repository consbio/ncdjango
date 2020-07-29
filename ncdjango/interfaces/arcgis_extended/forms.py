from ncdjango.interfaces.arcgis import forms
from . import form_fields


class GetImageForm(forms.GetImageForm):
    styles = form_fields.StyleField(required=False)


class LegendForm(forms.ArcGisFormBase):
    styles = form_fields.StyleField(required=False)
