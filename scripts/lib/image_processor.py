"""Image processing and compression functionality."""
import os
from PIL import Image
from typing import Dict, List, Optional, Tuple

class ImageProcessor:
    def __init__(self, config: Dict):
        """Initialize image processor with configuration."""
        self.config = config

    def process_image(self, input_path: str, output_path: str) -> bool:
        """Process a single image with compression and resizing."""
        try:
            with Image.open(input_path) as img:
                # Convert RGBA to RGB if necessary
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background

                # Calculate new dimensions while maintaining aspect ratio
                max_size = self.config['max_size']
                ratio = min(max_size/float(img.size[0]), max_size/float(img.size[1]))
                if ratio < 1:
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.LANCZOS)

                # Save with compression
                img.save(
                    output_path,
                    'JPEG',
                    quality=self.config['quality'],
                    optimize=True
                )
                return True
        except Exception as e:
            print(f"Error processing image {input_path}: {str(e)}")
            return False

    def get_compression_stats(self, original_path: str, compressed_path: str) -> Tuple[float, float, float]:
        """Get compression statistics for an image."""
        original_size = os.path.getsize(original_path)
        compressed_size = os.path.getsize(compressed_path)
        ratio = ((original_size - compressed_size) / original_size) * 100
        return ratio, original_size/1024/1024, compressed_size/1024/1024

    def is_valid_image(self, filename: str) -> bool:
        """Check if a file is a valid image based on its extension."""
        return any(filename.lower().endswith(ext) 
                  for ext in self.config['formats'])
