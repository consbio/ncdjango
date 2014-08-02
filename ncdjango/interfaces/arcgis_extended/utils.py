from clover.render.renderers.classified import ClassifiedRenderer
from clover.render.renderers.stretched import StretchedRenderer
from clover.render.renderers.unique import UniqueValuesRenderer
from clover.utilities.color import Color
import six


def get_renderer_from_definition(config):
    """Returns a renderer object based on the configuration (as a dictionary)"""

    options = config.get('options', {})

    try:
        renderer_type = config['type']
        renderer_colors = [(float(x[0]), hex_to_color(x[1])) for x in config['colors']]
        fill_value = options.get('fill_value')
        if fill_value is not None:
            fill_value = float(fill_value)
    except KeyError:
        raise ValueError("Missing required keys from renderer configuration")

    renderer_kwargs = {
        'colormap': renderer_colors,
        'fill_value': fill_value,
        'background_color': Color(255, 255, 255, 0)
    }

    if renderer_type == "stretched":
        color_space = options.get('color_space', 'hsv').lower().strip()
        if not color_space in ('rgb', 'hsv'):
            raise ValueError("Invalid color space: {}".format(color_space))

        renderer = StretchedRenderer(colorspace=color_space, **renderer_kwargs)
    elif renderer_type == "classified":
        renderer = ClassifiedRenderer(**renderer_kwargs)
    elif renderer_type == "unique":
        try:
            labels = [six.text_type(x) for x in options.get('labels', [])]
        except TypeError:
            raise ValueError("Labels option must be an array")

        renderer = UniqueValuesRenderer(labels=labels, **renderer_kwargs)

    return renderer


def hex_to_color(value):
    try:
        if value[0] == '#':
            value = value[1:]
        if len(value) == 3:
            value = ''.join([c*2 for c in value])
        if len(value) == 6:
            value = "{}ff".format(value)
        if len(value) != 8:
            raise ValueError

        color = []
        for i in range(0, 8, 2):
            color.append(int(value[i:i+2], 16))
        return Color(*color)

    except ValueError:
        raise ValueError("Invalid hex color: {}".format(value))