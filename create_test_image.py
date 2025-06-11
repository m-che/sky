#!/usr/bin/env python3
"""
Create a simple test image for upload testing
"""

import numpy as np
from PIL import Image

# Create a simple gradient image
width, height = 800, 600
image = np.zeros((height, width, 3), dtype=np.uint8)

# Create a blue-white gradient
for y in range(height):
    for x in range(width):
        # Gradient from blue to white
        blue = int(255 * (1 - y / height))
        image[y, x] = [255 - blue, 255 - blue, 255]

# Save the image
img = Image.fromarray(image)
img.save('/app/test_image.jpg')

print("Test image created successfully at /app/test_image.jpg")
