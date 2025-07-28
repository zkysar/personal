#!/usr/bin/env python3
"""Test script to verify featured image matching logic."""

import os
import sys
import json

# Add the lib directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from gallery_manager import GalleryManager

def test_featured_image_matching():
    """Test the featured image matching logic."""
    
    # Create a test gallery manager
    config_path = "/Users/zachkysar/git/personal/images/photography/gallery-config.json"
    gallery_manager = GalleryManager(config_path)
    
    # Load the current config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    gallery_manager.gallery_config = config
    
    # Test with Lizzie Waters group
    test_images = [
        {"compressed": "photography/Lizze/compressed/DSC09735-compressed.jpg"},
        {"compressed": "photography/Lizze/compressed/DSC09592-compressed.jpg"},  # This should match
        {"compressed": "photography/Lizze/compressed/DSC09733-compressed.jpg"}
    ]
    
    print("Testing featured image matching for Lizzie Waters...")
    print("Featured image: DSC09592.jpg")
    print("Available images:")
    for img in test_images:
        print(f"  - {img['compressed']}")
    
    # Update the group with test images
    gallery_manager.update_group_images("Lizze", test_images)
    
    # Check the result
    group = gallery_manager.get_group("Lizze")
    if group:
        print(f"\nResult:")
        print(f"Cover image: {group.get('coverImage', 'None')}")
        print(f"Expected: photography/Lizze/compressed/DSC09592-compressed.jpg")
        
        if "DSC09592" in group.get('coverImage', ''):
            print("✅ SUCCESS: Featured image matching works correctly!")
        else:
            print("❌ FAILED: Featured image matching is not working")
    else:
        print("❌ Group not found")

if __name__ == "__main__":
    test_featured_image_matching()
