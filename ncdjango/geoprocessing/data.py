import numpy
from clover.geometry.bbox import BBox


class Raster(numpy.ndarray):
    def __new__(cls, arr, extent, x_dim, y_dim, y_increasing=False):
        """Create a new Raster from a numpy array and a `BBox` object."""

        assert len(arr.shape) > 1
        assert isinstance(extent, BBox)

        obj = arr.view(cls)
        obj.x_dim = x_dim
        obj.y_dim = y_dim
        obj.extent = extent
        obj.y_increasing = y_increasing

        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return

        for attr in {'x_dim', 'y_dim', 'extent', 'y_increasing'}:
            setattr(self, attr, getattr(obj, attr, None))

    def __getitem__(self, items):
        arr = super(Raster, self).__getitem__(items)

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

                    end = item.stop or self.shape[self.x_dim]
                    if end < 0:
                        end = self.shape[self.x_dim] + end + 1

                    xmax -= cell_size[0] * (self.shape[self.x_dim] - end)

                if i == self.y_dim:
                    start = item.start or 0
                    end = item.stop or self.shape[self.y_dim]
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
