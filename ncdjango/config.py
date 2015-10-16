from clover.render.renderers.stretched import StretchedRenderer
from clover.render.renderers.unique import UniqueValuesRenderer
from clover.utilities.color import Color
from ncdjango import utils

DEFAULT_IMAGE_SIZE = (400, 400)
DEFAULT_IMAGE_FORMAT = "png"
DEFAULT_BACKGROUND_COLOR = Color(0, 0, 0, 0)


class ImageConfiguration(object):
    """Properties for the image request"""

    def __init__(self, **kwargs):
        self.extent = kwargs.get('extent')
        self.size = kwargs.get('size', DEFAULT_IMAGE_SIZE)
        self.image_format = kwargs.get('image_format', DEFAULT_IMAGE_FORMAT)
        self.background_color = kwargs.get('background_color', DEFAULT_BACKGROUND_COLOR)


class ConfigurationBase(object):
    """Base request configuration class"""

    def __init__(self, variable, time_index=None):
        self.variable = variable
        self.time_index = time_index

    def set_time_index_from_datetime(self, value, best_fit=True):
        """
        Sets the time_index parameter from a datetime using start/end/interval/units information from the service
        configuration. If best_fit is True, the method will match the closest time index for the given value, otherwise
        it will raise a ValueError for any value which doesn't exactly match a time index.
        """

        steps = self.variable.time_stops
        if value in steps:
            self.time_index = steps.index(value)
        elif best_fit:
            self.time_index = utils.best_fit(steps, value)
        else:
            raise ValueError("Invalid date")


class RenderConfiguration(ConfigurationBase):
    """Properties for rendering the variable"""

    def __init__(self, variable, **kwargs):
        super(RenderConfiguration, self).__init__(variable, time_index=kwargs.get('time_index'))

        self.renderer = kwargs.get('render', variable.renderer)
        self.time_index = kwargs.get('time_index')

    @property
    def hash(self):
        """
        Returns a hash of this render configuration from the variable, renderer, and time_index parameters. Used for
        caching the full-extent, native projection render so that subsequent requests can be served by a warp
        operation only.
        """

        renderer_str = "{}|{}|{}|{}".format(
            self.renderer.__class__.__name__, self.renderer.colormap, self.renderer.fill_value,
            self.renderer.background_color
        )
        if isinstance(self.renderer, StretchedRenderer):
            renderer_str = "{}|{}|{}".format(renderer_str, self.renderer.method, self.renderer.colorspace)
        elif isinstance(self.renderer, UniqueValuesRenderer):
            renderer_str = "{}|{}".format(renderer_str, self.renderer.labels)

        return hash("{}/{}/{}".format(self.variable.pk, renderer_str, self.time_index))


class IdentifyConfiguration(ConfigurationBase):
    """Properties for an identify value request"""

    def __init__(self, variable, geometry, projection, time_index=None):
        super(IdentifyConfiguration, self).__init__(variable, time_index=time_index)

        self.geometry = geometry
        self.projection = projection


class LegendConfiguration(ConfigurationBase):
    """Properties for a legends request"""

    def __init__(self, variable, renderer=None, size=[]):
        super(LegendConfiguration, self).__init__(variable)

        self.size = size
        self.renderer = renderer or variable.renderer
