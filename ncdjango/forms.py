from django.forms import ModelForm
from ncdjango.models import TemporaryFile


class TemporaryFileForm(ModelForm):
    class Meta:
        model = TemporaryFile
        fields = ('file',)