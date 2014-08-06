from ncdjango.interfaces.arcgis import forms
from ncdjango.interfaces.arcgis_extended.form_fields import StyleField


class GetImageForm(forms.GetImageForm):
    styles = StyleField(required=False)


class LegendForm(forms.ArcGisFormBase):
    styles = StyleField(required=False)