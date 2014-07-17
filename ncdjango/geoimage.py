from PIL import Image
from django.conf import settings
import math
import pyproj

WARP_MESH_SIZE = getattr(settings, 'NC_WARP_MESH_SIZE', 32)


class GeoImage(object):
    """An image with a geographic reference which can be warped to different geographic reference"""

    def __init__(self, image, bbox):
        self.image = image
        self.bbox = bbox

    def _create_mesh(self, target_bbox, target_size):
        to_target_world = image_to_world(target_bbox, target_size)
        to_target_image = world_to_image(target_bbox, target_size)
        to_source_image = world_to_image(self.bbox, self.image.size)

        # Determine mesh bounds
        source_bbox = self.bbox.project(target_bbox.projection)

        mesh_bounds = []
        mesh_bounds.extend(to_target_image(*(source_bbox.xmin, source_bbox.ymax)))
        mesh_bounds.extend(to_target_image(*(source_bbox.xmax, source_bbox.ymin)))

        mesh_bounds = [
            max(mesh_bounds[0], 0),
            max(mesh_bounds[1], 0),
            min(mesh_bounds[2], target_size[0]),
            min(mesh_bounds[3], target_size[1])
        ]

        step = ((mesh_bounds[2]-mesh_bounds[0]) / WARP_MESH_SIZE, (mesh_bounds[3]-mesh_bounds[1]) / WARP_MESH_SIZE)
        mesh = []

        for i in range(WARP_MESH_SIZE):
            y = i*step[1] + mesh_bounds[1]

            for j in range(WARP_MESH_SIZE):
                x = j*step[0] + mesh_bounds[0]

                # Target px
                target_rect_px = [
                    int(math.ceil(x)), int(math.ceil(y)), int(math.ceil(x+step[0])), int(math.ceil(y+step[1]))
                ]

                # Adjust to end of image if necessary
                if i == WARP_MESH_SIZE-1:
                    target_rect_px[3] = int(math.ceil(mesh_bounds[3]))
                if j == WARP_MESH_SIZE-1:
                    target_rect_px[2] = int(math.ceil(mesh_bounds[2]))

                # Make sure target box isn't 0 width or height
                if target_rect_px[0] == target_rect_px[2]:
                    target_rect_px[2] = target_rect_px[0]+1
                if target_rect_px[1] == target_rect_px[3]:
                    target_rect_px[3] = target_rect_px[1]+1

                # Source world
                source_quad = [ ]
                points = (
                    (target_rect_px[0], target_rect_px[1]),
                    (target_rect_px[0], target_rect_px[3]),
                    (target_rect_px[2], target_rect_px[3]),
                    (target_rect_px[2], target_rect_px[1])
                )
                for point in points:
                    source_quad.extend(pyproj.transform(
                        target_bbox.projection, self.bbox.projection, *to_target_world(*point)
                    ))

                # Longitude coordinates at or across 180 swap from negative to positive, which throws off the mesh.
                if self.bbox.projection.is_latlong() and source_quad[0] > source_quad[4]:
                    if x < (mesh_bounds[2]-mesh_bounds[0])/2.0 + mesh_bounds[0]:
                        source_quad[0] = -180.0 - (180-abs(source_quad[0]))
                    else:
                        source_quad[4] = 180.0 + (180-abs(source_quad[4]))
                if self.bbox.projection.is_latlong() and source_quad[2] > source_quad[6]:
                    if x < (mesh_bounds[2]-mesh_bounds[0])/2.0 + mesh_bounds[0]:
                        source_quad[2] = -180.0 - (180-abs(source_quad[2]))
                    else:
                        source_quad[6] = 180.0 + (180-abs(source_quad[6]))

                # Source px
                source_quad_px = [ ]
                for k in range(0,8,2):
                    source_quad_px.extend(to_source_image(source_quad[k],source_quad[k+1]))

                mesh.append((tuple(target_rect_px), tuple(source_quad_px)))

        return mesh

    def warp(self, target_bbox, target_size=None):
        """Returns a copy of this image warped to a target size and bounding box"""

        # Determine target size based on pixels per unit of the source image and the target bounding box reprojected
        # to the source projection.
        if not target_size:
            px_per_unit = (float(self.image.size[0])/self.bbox.width, float(self.image.size[1])/self.bbox.height)
            src_bbox = target_bbox.project(self.bbox.projection)
            target_size = (int(round(src_bbox.width*px_per_unit[0])), int(round(src_bbox.height*px_per_unit[1])))

        # If target and source bounds are the same and source and target sizes are the same, return a reference to
        # this image.
        if self.bbox == target_bbox and self.image.size == target_size:
            return self

        # If target and source projections are the same, perform a simple resize
        elif self.bbox.projection.srs == target_bbox.projection.srs:
            to_source_image = world_to_image(self.bbox, self.image.size)
            upper_left = to_source_image(*(target_bbox.xmin, target_bbox.ymax))
            lower_right = to_source_image(*(target_bbox.xmax, target_bbox.ymin))

            new_image = self.image.transform(
                target_size, Image.EXTENT, (upper_left[0], upper_left[1], lower_right[0], lower_right[1]),
                Image.NEAREST
            )

        # Full warp
        else:
            canvas_size = (
                max(target_size[0], self.image.size[0]),
                max(target_size[1], self.image.size[1])
            )
            im = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            im.paste(self.image, (0, 0))
            new_image = im.transform(
                target_size, Image.MESH, self._create_mesh(target_bbox, target_size), Image.NEAREST
            )

        return GeoImage(new_image, target_bbox)


def world_to_image(bbox, size):
    """Function generator to create functions for converting from world coordinates to image coordinates"""

    px_per_unit = (float(size[0])/bbox.width, float(size[1]/bbox.height))
    return lambda x,y: ((x-bbox.xmin) * px_per_unit[0], size[1] - (y-bbox.ymin)*px_per_unit[1])


def image_to_world(bbox, size):
    """Function generator to create functions for converting from image coordinates to world coordinates"""

    px_per_unit = (float(size[0])/bbox.width, float(size[1]/bbox.height))
    return lambda x,y: (x/px_per_unit[0] + bbox.xmin, (size[1]-y)/px_per_unit[1] + bbox.ymin)