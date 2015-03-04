import math
from clover.geometry.bbox import BBox
from django.conf import settings

MAX_CHUNK_DIMENSIONS = getattr(settings, 'NC_MAX_CHUNK_DIMENSIONS', (500, 500))


class Chunk(object):
    """Represents a single "chunk" of a chunked grid"""

    def __init__(self, x_index, y_index, x_min, y_min, x_max, y_max, bbox):
        self.x_index = x_index
        self.y_index = y_index
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.bbox = bbox


class ChunkedGrid(object):
    """
    Given the dimensions chunk and bounding box of a full grid, generates "chunks" according to the max dimensions
    """

    def __init__(self, grid_dimensions, bbox, is_y_increasing, max_chunk_dimensions=MAX_CHUNK_DIMENSIONS):
        self.grid_dimensions = grid_dimensions
        self.bbox = bbox
        self.is_y_increasing = is_y_increasing
        self.max_chunk_dimensions = max_chunk_dimensions

    def chunks(self):
        """Returns a chunk iterator"""

        x_count = max(int(math.ceil(float(self.grid_dimensions[0]) / float(self.max_chunk_dimensions[0]))), 1)
        y_count = max(int(math.ceil(float(self.grid_dimensions[1]) / float(self.max_chunk_dimensions[1]))), 1)
        cell_size = (
            float(self.bbox.width) / float(self.grid_dimensions[0]),
            float(self.bbox.height) / float(self.grid_dimensions[1])
        )

        for i in range(y_count):
            y_min = self.max_chunk_dimensions[1] * i
            y_max = min(y_min + self.max_chunk_dimensions[1], self.grid_dimensions[1])
            height = y_max - y_min

            if self.is_y_increasing:
                bbox_y_min = self.bbox.ymin + y_min*cell_size[1]
                bbox_y_max = bbox_y_min + height*cell_size[1]
            else:
                bbox_y_max = self.bbox.ymax - y_min*cell_size[1]
                bbox_y_min = bbox_y_max - height*cell_size[1]

            for j in range(x_count):
                x_min = self.max_chunk_dimensions[0] * j
                x_max = min(x_min + self.max_chunk_dimensions[0], self.grid_dimensions[0])
                width = x_max - x_min

                bbox_x_min = self.bbox.xmin + x_min*cell_size[0]
                bbox_x_max = bbox_x_min + width*cell_size[0]

                bbox = BBox((bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max), projection=self.bbox.projection)

                yield Chunk(j, i, x_min, y_min, x_max, y_max, bbox)