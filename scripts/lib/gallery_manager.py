"""Gallery configuration management."""
import json
from typing import Dict, List, Optional

class GalleryManager:
    def __init__(self, config_path: str):
        """Initialize gallery manager with config file path."""
        self.config_path = config_path
        self.gallery_config = self._load_config()

    def _load_config(self) -> Dict:
        """Load gallery configuration from JSON file."""
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get_group(self, group_id: str) -> Optional[Dict]:
        """Get a group by its ID."""
        return next(
            (g for g in self.gallery_config['groups'] if g['id'] == group_id),
            None
        )

    def create_or_update_group(self, group_id: str, title: str, description: str, cover_image: str = None) -> Dict:
        """Create a new group or update existing group metadata."""
        group = self.get_group(group_id)
        if not group:
            group = {
                'id': group_id,
                'title': title,
                'description': description,
                'images': []
            }
            self.gallery_config['groups'].append(group)
        else:
            group['title'] = title
            group['description'] = description

        if cover_image:
            group['coverImage'] = cover_image

        self._save_config()
        return group

    def update_group_images(self, group_id: str, images: List[Dict]):
        """Update a group's images and save the configuration."""
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Group {group_id} not found in gallery config")

        group['images'] = images
        if images:
            group['coverImage'] = images[0]['compressed']

        self._save_config()

    def _save_config(self):
        """Save the current configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.gallery_config, f, indent=2)
        except Exception as e:
            print(f"Error saving gallery config: {str(e)}")
            raise
