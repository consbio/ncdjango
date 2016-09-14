import numpy
from clover.geometry.bbox import BBox
from numpy.ma.core import is_masked


class Raster(numpy.ma.MaskedArray):
    def __new__(cls, arr, extent, x_dim, y_dim, y_increasing=False):
        """Create a new Raster from a numpy array and a `BBox` object."""

        assert len(arr.shape) > 1
        assert isinstance(extent, BBox)

        obj = numpy.asarray(arr).view(cls)
        obj.x_dim = x_dim
        obj.y_dim = y_dim
        obj.extent = extent
        obj.y_increasing = y_increasing
        obj.__array_priority__ = 100

        if is_masked(arr):
            obj._mask = arr._mask
            obj._fill_value = arr._fill_value

        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return

        for attr in {'x_dim', 'y_dim', 'extent', 'y_increasing'}:
            setattr(self, attr, getattr(obj, attr, None))

        super(Raster, self).__array_finalize__(obj)

    def __getitem__(self, items):
        arr = super(Raster, self).__getitem__(items)
        Raster.__array_finalize__(arr, self)

        if self.extent is None or self.x_dim is None or self.y_dim is None:
            return arr.view(numpy.ndarray)  # Cast back to regular numpy array

        if isinstance(items, slice):
            items = (items,)

        if isinstance(items, tuple):
            xmin, ymin, xmax, ymax = self.extent.as_list()
            cell_size = (self.extent.width / self.shape[self.x_dim], self.extent.height / self.shape[self.y_dim])
            has_valid_extent = True

            for i, item in enumerate(items):
                if not isinstance(item, slice) and i in {self.x_dim, self.y_dim}:
                    # Not a slice, so we can't reliably preserve extent information
                    has_valid_extent = False
                    break

                if i == self.x_dim:
                    xmin += cell_size[0] * (item.start or 0)

                    end = min(item.stop or self.shape[self.x_dim], self.shape[self.x_dim])
                    if end < 0:
                        end = self.shape[self.x_dim] + end + 1

                    xmax -= cell_size[0] * (self.shape[self.x_dim] - end)

                if i == self.y_dim:
                    start = item.start or 0
                    end = min(item.stop or self.shape[self.y_dim], self.shape[self.y_dim])
                    if end < 0:
                        end = self.shape[self.y_dim] + end
                    end = self.shape[self.y_dim] - end

                    if not self.y_increasing:
                        start, end = end, start

                    ymin += cell_size[1] * start
                    ymax -= cell_size[1] * end

            if has_valid_extent:
                arr.extent = BBox((xmin, ymin, xmax, ymax), projection=self.extent.projection)
                return arr
            else:
                return arr.view(numpy.ndarray)

        return arr.view(numpy.ndarray)

    def astype(self, newtype):
        output = super(Raster, self).astype(newtype)
        Raster.__array_finalize__(output, self)

        return output

    def __eq__(self, other):
        obj = super(Raster, self).__eq__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __ne__(self, other):
        obj = super(Raster, self).__ne__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __add__(self, other):
        obj = super(Raster, self).__add__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __radd__(self, other):
        obj = super(Raster, self).__radd__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __sub__(self, other):
        obj = super(Raster, self).__sub__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rsub__(self, other):
        obj = super(Raster, self).__rsub__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __mul__(self, other):
        obj = super(Raster, self).__mul__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rmul__(self, other):
        obj = super(Raster, self).__rmul__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __div__(self, other):
        obj = super(Raster, self).__div__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rdiv__(self, other):
        obj = super(Raster, self).__rdiv__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __floordiv__(self, other):
        obj = super(Raster, self).__floordiv__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rfloordiv__(self, other):
        obj = super(Raster, self).__rfloordiv__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __truediv__(self, other):
        obj = super(Raster, self).__truediv__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rtruediv__(self, other):
        obj = super(Raster, self).__rtruediv__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __mod__(self, other):
        obj = super(Raster, self).__mod__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rmod__(self, other):
        obj = super(Raster, self).__rmod__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __pow__(self, other):
        obj = super(Raster, self).__pow__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rpow__(self, other):
        obj = super(Raster, self).__pow__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __lshift__(self, other):
        obj = super(Raster, self).__lshift__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rlshift__(self, other):
        obj = super(Raster, self).__rlshift__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rshift__(self, other):
        obj = super(Raster, self).__lshift__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rrshift__(self, other):
        obj = super(Raster, self).__rrshift__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __and__(self, other):
        obj = super(Raster, self).__and__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rand__(self, other):
        obj = super(Raster, self).__rand__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __xor__(self, other):
        obj = super(Raster, self).__xor__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __rxor__(self, other):
        obj = super(Raster, self).__rxor__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __or__(self, other):
        obj = super(Raster, self).__or__(other)
        Raster.__array_finalize__(obj, self)
        return obj

    def __ror__(self, other):
        obj = super(Raster, self).__ror__(other)
        Raster.__array_finalize__(obj, self)
        return obj


def is_raster(arr):
    """Determine whether the array is a `Raster`"""

    return isinstance(arr, Raster) or hasattr(arr, 'extent')
