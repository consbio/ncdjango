from ncdjango.interfaces.arcgis import views
from . import forms


class GetImageView(views.GetImageView):
    form_class = forms.GetImageForm

    def get_render_configurations(self, request, **kwargs):
        base_config, configurations = super(GetImageView, self).get_render_configurations(request, **kwargs)
        styles = self.form_data.get('styles')

        if styles:
            for config in configurations:
                config.renderer = styles.get(config.variable.index, config.renderer)

        return base_config, configurations


class LegendView(views.LegendView):
    form_class = forms.LegendForm

    def get_legend_configurations(self, request, **kwargs):
        configurations = super(LegendView, self).get_legend_configurations(request, **kwargs)
        self.process_form_data({'response_format': 'html'}, kwargs)
        styles = self.form_data.get('styles')

        if styles:
            for config in configurations:
                config.renderer = styles.get(config.variable.index, config.renderer)

        return configurations
