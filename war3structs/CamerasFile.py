from construct import *
from war3structs.common import *

"""
  Formats: w3c
  Version: 0

  The cameras file contains the cameras in a map.
"""

Camera = Struct(
  "target_x" / Float,
  "target_y" / Float,
  "offset_z" / Float,
  "rotation" / Float, # in degrees
  "angle_of_attack" / Float, # in degrees
  "distance" / Float,
  "roll" / Float,
  "field_of_view" / Float, # in degrees
  "far_clipping" / Float,
  "unknown" / Float, # ? (usually 100)
  "name" / String
)

CamerasFile = Struct(
  "version" / Integer,
  "cameras_count" / Integer,
  "cameras" / Array(this.cameras_count, Camera)
)
