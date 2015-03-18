from PIL import Image
from django.conf import settings
import math
import pyproj

MAX_MESH_DEPTH = getattr(settings, 'NC_WARP_MAX_DEPTH', 5)
PROJECTION_THRESHOLD = getattr(settings, 'NC_WARP_PROJECTION_THRESHOLD', 1.5)  # Warp tolerance in pixels


class GeoImage(object):
    """An image with a geographic reference which can be warped to different geographic reference"""

    def __init__(self, image, bbox):
        self.image = image
        self.bbox = bbox

    def _get_mesh_piece(self, bounds, target_projection, to_target_world, to_target_image, to_source_image, depth=0):
        target_rect_px = [
            int(math.ceil(bounds[0])),
            int(math.ceil(bounds[1])),
            int(math.ceil(bounds[2])),
            int(math.ceil(bounds[3]))
        ]

        # Make sure target box isn't 0 width or height
        if target_rect_px[0] == target_rect_px[2]:
            target_rect_px[2] = target_rect_px[0]+1
        if target_rect_px[1] == target_rect_px[3]:
            target_rect_px[3] = target_rect_px[1]+1

        source_quad = []
        points = (
            (target_rect_px[0], target_rect_px[1]),
            (target_rect_px[0], target_rect_px[3]),
            (target_rect_px[2], target_rect_px[3]),
            (target_rect_px[2], target_rect_px[1])
        )
        for point in points:
            source_quad.extend(pyproj.transform(
                target_projection, self.bbox.projection, *to_target_world(*point)
            ))

        # Midpoint in target pixel space
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        target_midpoint_px = (bounds[2] - width/2.0, bounds[3] - height/2.0)

        # Midpoint in source world projected to target pixel space
        width = source_quad[4] - source_quad[0]
        height = source_quad[5] - source_quad[1]
        source_midpoint = (source_quad[4] - width/2.0, source_quad[5] - height/2.0)
        projected_midpoint = pyproj.transform(self.bbox.projection, target_projection, *source_midpoint)
        projected_midpoint_px = to_target_image(*projected_midpoint)

        # Compare the "guessed" midpoint with actual, projected midpoint
        difference = math.sqrt(
            (projected_midpoint_px[0]-target_midpoint_px[0])**2 + (projected_midpoint_px[1]-target_midpoint_px[1])**2
        )

        if difference > PROJECTION_THRESHOLD and depth < MAX_MESH_DEPTH:
            return (
                self._get_mesh_piece(
                    (bounds[0], bounds[1], target_midpoint_px[0], target_midpoint_px[1]), target_projection,
                    to_target_world, to_target_image, to_source_image, depth+1
                ) +
                self._get_mesh_piece(
                    (target_midpoint_px[0], bounds[1], bounds[2], target_midpoint_px[1]), target_projection,
                    to_target_world, to_target_image, to_source_image, depth+1
                ) +
                self._get_mesh_piece(
                    (bounds[0], target_midpoint_px[1], target_midpoint_px[0], bounds[3]), target_projection,
                    to_target_world, to_target_image, to_source_image, depth+1
                ) +
                self._get_mesh_piece(
                    (target_midpoint_px[0], target_midpoint_px[1], bounds[2], bounds[3]), target_projection,
                    to_target_world, to_target_image, to_source_image, depth+1
                )
            )
        else:
            # Longitude coordinates at or across 180 swap from negative to positive, which throws off the mesh.
            if self.bbox.projection.is_latlong() and source_quad[0] > source_quad[4]:
                if target_rect_px[0] < (bounds[2]-bounds[0])/2.0 + bounds[0]:
                    source_quad[0] = -180.0 - (180-abs(source_quad[0]))
                else:
                    source_quad[4] = 180.0 + (180-abs(source_quad[4]))
            if self.bbox.projection.is_latlong() and source_quad[2] > source_quad[6]:
                if target_rect_px[0] < (bounds[2]-bounds[0])/2.0 + bounds[0]:
                    source_quad[2] = -180.0 - (180-abs(source_quad[2]))
                else:
                    source_quad[6] = 180.0 + (180-abs(source_quad[6]))

            # Source px
            source_quad_px = []
            for k in range(0, 8, 2):
                source_quad_px.extend(to_source_image(source_quad[k], source_quad[k+1]))

            return [(tuple(target_rect_px), tuple(source_quad_px))]

    def _create_mesh(self, target_bbox, target_size):
        to_target_world = image_to_world(target_bbox, target_size)
        to_target_image = world_to_image(target_bbox, target_size)
        to_source_image = world_to_image(self.bbox, self.image.size)

        source_bbox = self.bbox.project(target_bbox.projection)

        mesh_bounds = []
        mesh_bounds.extend(to_target_image(source_bbox.xmin, source_bbox.ymax))
        mesh_bounds.extend(to_target_image(source_bbox.xmax, source_bbox.ymin))

        mesh_bounds = [
            max(mesh_bounds[0], 0),
            max(mesh_bounds[1], 0),
            min(mesh_bounds[2], target_size[0]),
            min(mesh_bounds[3], target_size[1])
        ]

        return self._get_mesh_piece(
            mesh_bounds, target_bbox.projection, to_target_world, to_target_image, to_source_image
        )

    def warp(self, target_bbox, target_size=None):
        """Returns a copy of this image warped to a target size and bounding box"""

        # Determine target size based on pixels per unit of the source image and the target bounding box reprojected
        # to the source projection.
        if not target_size:
            px_per_unit = (float(self.image.size[0])/self.bbox.width, float(self.image.size[1])/self.bbox.height)
            src_bbox = target_bbox.project(self.bbox.projection)
            target_size = (int(round(src_bbox.width*px_per_unit[0])), int(round(src_bbox.height*px_per_unit[1])))

        canvas_size = (
            max(target_size[0], self.image.size[0]),
            max(target_size[1], self.image.size[1])
        )

        # If target and source bounds are the same and source and target sizes are the same, return a reference to
        # this image.
        if self.bbox == target_bbox and self.image.size == target_size:
            return self

        # If target and source projections are the same, perform a simple resize
        elif self.bbox.projection.srs == target_bbox.projection.srs:
            to_source_image = world_to_image(self.bbox, self.image.size)
            upper_left = to_source_image(*(target_bbox.xmin, target_bbox.ymax))
            lower_right = to_source_image(*(target_bbox.xmax, target_bbox.ymin))

            if canvas_size == self.image.size:
                im = self.image
            else:
                im = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                im.paste(self.image, (0, 0))

            new_image = im.transform(
                target_size, Image.EXTENT, (upper_left[0], upper_left[1], lower_right[0], lower_right[1]),
                Image.NEAREST
            )

        # Full warp
        else:
            if canvas_size == self.image.size:
                im = self.image
            else:
                im = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                im.paste(self.image, (0, 0))

            new_image = im.transform(
                target_size, Image.MESH, self._create_mesh(target_bbox, target_size), Image.NEAREST
            )

        return GeoImage(new_image, target_bbox)


def world_to_image(bbox, size):
    """Function generator to create functions for converting from world coordinates to image coordinates"""

    px_per_unit = (float(size[0])/bbox.width, float(size[1])/bbox.height)
    return lambda x,y: ((x-bbox.xmin) * px_per_unit[0], size[1] - (y-bbox.ymin)*px_per_unit[1])


def image_to_world(bbox, size):
    """Function generator to create functions for converting from image coordinates to world coordinates"""

    px_per_unit = (float(size[0])/bbox.width, float(size[1]/bbox.height))
    return lambda x,y: (x/px_per_unit[0] + bbox.xmin, (size[1]-y)/px_per_unit[1] + bbox.ymin)