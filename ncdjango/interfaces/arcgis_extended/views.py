from ncdjango.interfaces.arcgis import views
from ncdjango.interfaces.arcgis_extended.forms import GetImageForm


class GetImageView(views.GetImageView):
    form_class = GetImageForm

    def get_render_configurations(self, request, **kwargs):
        configurations = super(GetImageView, self).get_render_configurations(request, **kwargs)
        styles = self.form_data.get('styles')

        if styles:
            for config in configurations:
                config.renderer = styles.get(config.variable.index, config.renderer)

        return configurations