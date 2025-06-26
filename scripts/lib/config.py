"""Configuration management for image processing scripts."""
import os
import json
from typing import Dict

class Config:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self._validate_config()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)

    def _validate_config(self):
        """Validate required configuration fields."""
        required_fields = {
            's3': ['bucket', 'region', 'base_path'],
            'image_processing': ['max_size', 'quality', 'formats'],
            'paths': ['gallery_config', 'image_dirs']
        }

        for section, fields in required_fields.items():
            if section not in self.config:
                raise ValueError(f"Missing required section: {section}")
            for field in fields:
                if field not in self.config[section]:
                    raise ValueError(f"Missing required field: {section}.{field}")

    def get_s3_config(self) -> Dict:
        """Get S3-related configuration."""
        return self.config['s3']

    def get_image_processing_config(self) -> Dict:
        """Get image processing configuration."""
        return self.config['image_processing']

    def get_gallery_config_path(self) -> str:
        """Get the gallery configuration file path."""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            self.config['paths']['gallery_config']
        )

    def get_image_dirs(self) -> list[str]:
        """Get the list of image directory paths."""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return [os.path.join(base_dir, path) for path in self.config['paths']['image_dirs']]
