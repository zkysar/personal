"""Gallery configuration management."""
import json
import os
from typing import Dict, List, Optional

class GalleryManager:
    def __init__(self, config_path: str):
        """Initialize gallery manager with config file path."""
        self.config_path = config_path
        self.gallery_config = {'groups': []}

    def regenerate_from_groups(self, group_directories: List[str]):
        """Completely regenerate gallery config from group directories.
        
        Args:
            group_directories: List of paths to group directories containing config.json files
                              Following pattern: photography_collection/date_captured/group_name/...
        """
        print("Regenerating gallery-config.json from scratch...")
        self.gallery_config = {'groups': []}
        
        for group_dir in group_directories:
            try:
                config_path = os.path.join(group_dir, 'config.json')
                if not os.path.exists(config_path):
                    print(f"Warning: No config.json found in {group_dir}, skipping...")
                    continue
                    
                # Read group configuration
                with open(config_path, 'r') as f:
                    group_config = json.load(f)
                
                # Extract date from directory structure: .../date_captured/group_name/...
                path_parts = group_dir.split(os.sep)
                if len(path_parts) < 2:
                    print(f"Warning: Invalid directory structure for {group_dir}, skipping...")
                    continue
                    
                date_captured = path_parts[-2]  # Parent directory should be the date
                group_name = path_parts[-1]     # Current directory is the group name
                
                # Generate title and description from config contents
                name = group_config.get('name', group_name)
                location = group_config.get('location', '')
                url = group_config.get('url', '')  # Extract URL if present
                featured_image = group_config.get('featured_image', '')  # Extract featured image
                
                # Generate title from name
                title = name
                
                # Generate description from name, location, and date
                if location:
                    description = f"{name} at {location} on {date_captured}."
                else:
                    description = f"{name} on {date_captured}."
                
                # Use group name as ID
                group_id = group_name
                
                # Create group entry with date information
                group = {
                    'id': group_id,
                    'title': title,
                    'description': description,
                    'date_captured': date_captured,  # Add date from directory structure
                    'images': [],
                    'coverImage': '',
                    'featured_image': featured_image  # Store featured image from config
                }
                
                # Add URL field if present in config
                if url:
                    group['url'] = url
                
                self.gallery_config['groups'].append(group)
                print(f"Added group: {group_id} - {title} (captured: {date_captured})")
                
            except Exception as e:
                print(f"Error processing group directory {group_dir}: {str(e)}")
                continue
        
        # Save the regenerated config
        self._save_config()
        print(f"Gallery config regenerated with {len(self.gallery_config['groups'])} groups")

    def get_group(self, group_id: str) -> Optional[Dict]:
        """Get a group by its ID."""
        return next(
            (g for g in self.gallery_config['groups'] if g['id'] == group_id),
            None
        )

    def update_group_images(self, group_id: str, images: List[Dict]):
        """Update a group's images and save the configuration."""
        group = self.get_group(group_id)
        if not group:
            print(f"Warning: Group {group_id} not found in gallery config, skipping image update")
            return

        group['images'] = images
        if images:
            # Use featured_image if specified, otherwise fall back to first image
            featured_image = group.get('featured_image', '')
            if featured_image:
                # Find the featured image in the images list
                # Extract base filename without extension for matching
                import os
                featured_base = os.path.splitext(featured_image)[0]  # Remove .jpg extension
                
                featured_img = None
                for img in images:
                    if 'original' in img and img['original'].endswith(featured_image):
                        featured_img = img
                        break
                    elif 'compressed' in img:
                        # Extract the base filename from the compressed path
                        compressed_path = img['compressed']
                        compressed_filename = os.path.basename(compressed_path)  # Get just the filename
                        compressed_base = os.path.splitext(compressed_filename)[0]  # Remove extension
                        
                        # Remove the '-compressed' suffix to get the original base name
                        if compressed_base.endswith('-compressed'):
                            compressed_base = compressed_base[:-11]  # Remove '-compressed'
                        
                        # Match the base names
                        if featured_base == compressed_base:
                            featured_img = img
                            break
            
                if featured_img:
                    group['coverImage'] = featured_img['compressed']
                    print(f"Using featured image {featured_image} as cover for {group_id}")
                else:
                    print(f"Warning: Featured image {featured_image} not found for {group_id}, using first image")
                    group['coverImage'] = images[0]['compressed']
            else:
                group['coverImage'] = images[0]['compressed']

        self._save_config()

    def _save_config(self):
        """Save the current configuration to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.gallery_config, f, indent=2)
        except Exception as e:
            print(f"Error saving gallery config: {str(e)}")
            raise
