#!/usr/bin/env python3
import os
import sys
import json
import argparse
from typing import List, Dict

from lib.config import Config
from lib.image_processor import ImageProcessor
from lib.s3_uploader import S3Uploader
from lib.gallery_manager import GalleryManager

def has_image_files(directory: str) -> bool:
    """Check if a directory contains image files.
    
    Args:
        directory: Directory path to check
        
    Returns:
        True if directory contains image files, False otherwise
    """
    if not os.path.exists(directory):
        return False
        
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    for filename in os.listdir(directory):
        if os.path.splitext(filename.lower())[1] in image_extensions:
            return True
    
    return False

def discover_group_directories(photography_collection_path: str) -> List[str]:
    """Discover all group directories following the strict pattern: photography_collection/date_captured/group_name/...
    
    Args:
        photography_collection_path: Path to the photography collection directory
        
    Returns:
        List of directory paths that contain images and follow the required structure
        
    Raises:
        SystemExit: If any directory doesn't follow the required pattern
    """
    group_dirs = []
    
    if not os.path.exists(photography_collection_path):
        return group_dirs
    
    # Only look at date directories (first level)
    for date_dir_name in os.listdir(photography_collection_path):
        date_dir_path = os.path.join(photography_collection_path, date_dir_name)
        
        # Skip non-directories and system files
        if not os.path.isdir(date_dir_path) or date_dir_name.startswith('.'):
            continue
            
        # Validate date directory name format (YYYY-MM-DD)
        if not validate_date_directory_name(date_dir_name):
            print(f"❌ ERROR: Top-level directory '{date_dir_name}' does not follow YYYY-MM-DD format")
            print(f"   Required structure: photography_collection/YYYY-MM-DD/group_name/...")
            raise SystemExit(1)
        
        # Look at group directories (second level)
        for group_dir_name in os.listdir(date_dir_path):
            group_dir_path = os.path.join(date_dir_path, group_dir_name)
            
            # Skip non-directories, system files, and compressed directories
            if not os.path.isdir(group_dir_path) or group_dir_name.startswith('.') or group_dir_name == 'compressed':
                continue
                
            # Check if this group directory contains images
            if has_image_files(group_dir_path):
                group_dirs.append(group_dir_path)
    
    return group_dirs

def validate_date_directory_name(dir_name: str) -> bool:
    """Validate that directory name follows YYYY-MM-DD format.
    
    Args:
        dir_name: Directory name to validate
        
    Returns:
        True if valid date format, False otherwise
    """
    import re
    from datetime import datetime
    
    # Check format with regex
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, dir_name):
        return False
    
    # Validate it's a real date
    try:
        datetime.strptime(dir_name, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_group_directories(group_dirs: List[str]) -> Dict[str, List[str]]:
    """Validate that group directories meet requirements.
    
    Args:
        group_dirs: List of group directory paths
        
    Returns:
        Dictionary with validation errors:
        {
            'missing_config': [list of dirs missing config.json],
            'has_subdirectories': [list of dirs with subdirectories]
        }
    """
    validation_errors = {
        'missing_config': [],
        'has_subdirectories': []
    }
    
    for group_dir in group_dirs:
        # Check for config.json
        config_path = os.path.join(group_dir, 'config.json')
        if not os.path.exists(config_path):
            validation_errors['missing_config'].append(group_dir)
        
        # Check for subdirectories (ignore compressed directories)
        try:
            for item in os.listdir(group_dir):
                item_path = os.path.join(group_dir, item)
                if os.path.isdir(item_path) and item != 'compressed':
                    validation_errors['has_subdirectories'].append(group_dir)
                    break  # Found one non-compressed subdirectory, that's enough
        except OSError:
            continue  # Skip if we can't read the directory
    
    return validation_errors

def compress_images(source_dir, output_dir, quality=85, max_size=1200):
    """
    Compress and resize images from source directory to output directory.
    
    Args:
        source_dir (str): Source directory containing original images
        output_dir (str): Output directory for compressed images
        quality (int): JPEG quality (1-100)
        max_size (int): Maximum width or height in pixels
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get list of image files
    image_files = [f for f in os.listdir(source_dir) 
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    total_files = len(image_files)
    processed = 0
    
    for filename in image_files:
        try:
            # Open image
            with Image.open(os.path.join(source_dir, filename)) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate new dimensions while maintaining aspect ratio
                ratio = min(max_size/max(img.size[0], img.size[1]), 1.0)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                
                # Resize if necessary
                if ratio < 1.0:
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Prepare output filename
                output_filename = os.path.splitext(filename)[0] + '-compressed.jpg'
                output_path = os.path.join(output_dir, output_filename)
                
                # Save compressed image
                img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                # Calculate compression ratio
                original_size = os.path.getsize(os.path.join(source_dir, filename))
                compressed_size = os.path.getsize(output_path)
                ratio = (1 - compressed_size/original_size) * 100
                
                processed += 1
                print(f"[{processed}/{total_files}] Compressed {filename}")
                print(f"    Size reduced by {ratio:.1f}% ({original_size/1024/1024:.1f}MB → {compressed_size/1024/1024:.1f}MB)")
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

def process_group(config_path: str, group_id: str = None, source_dir: str = None) -> None:
    """Process images for a gallery group.
    
    Args:
        config_path: Path to configuration file
        group_id: Optional group ID override
        source_dir: Optional source directory override
    """
    try:
        # Initialize components
        config = Config(config_path)
        gallery_manager = GalleryManager(config.get_gallery_config_path())
        image_processor = ImageProcessor(config.get_image_processing_config())
        s3_uploader = S3Uploader(config.get_s3_config())
        
        # Discover all group directories (directories containing images)
        photography_collection_path = config.get_photography_collection_path()
        print(f"Discovering group directories in: {photography_collection_path}")
        
        group_dirs = discover_group_directories(photography_collection_path)
        if not group_dirs:
            print("\n⚠️  No directories containing images found in the photography collection.")
            return
        
        print(f"Found {len(group_dirs)} directories containing images.")
        
        # Validate all group directories and fail fast if any don't meet requirements
        validation_errors = validate_group_directories(group_dirs)
        
        has_errors = False
        
        if validation_errors['missing_config']:
            print("\n❌ ERROR: The following group directories are missing config.json files:")
            for missing_dir in validation_errors['missing_config']:
                print(f"   - {missing_dir}")
            has_errors = True
        
        if validation_errors['has_subdirectories']:
            print("\n❌ ERROR: The following group directories contain subdirectories (not allowed):")
            for subdir_dir in validation_errors['has_subdirectories']:
                print(f"   - {subdir_dir}")
            has_errors = True
        
        if has_errors:
            print("\nGroup directory requirements:")
            print("  1. Must contain a config.json file with: {'name': 'Display Name', 'description': 'Description'}")
            print("  2. Must not contain any subdirectories (only image files allowed)")
            print("\nPlease fix these issues before running the script.")
            raise SystemExit(1)
        
        # Regenerate gallery config from scratch using all discovered group directories
        print("\n=== Regenerating gallery configuration ===")
        gallery_manager.regenerate_from_groups(group_dirs)
        
        # Delete entire collection from S3 before re-uploading
        print("\n=== Deleting existing collection from S3 ===")
        if not s3_uploader.delete_collection():
            print("Warning: Failed to delete existing collection from S3. Continuing with upload...")

        # Use provided source dir or get all discovered group directories
        source_dirs = [source_dir] if source_dir else group_dirs

        for source_dir in source_dirs:
            # Use directory name as group ID if none provided
            current_group_id = group_id or os.path.basename(source_dir)
            
            processed_images = []
            # Create permanent compressed directory for caching
            compressed_dir = os.path.join(source_dir, 'compressed')
            if not os.path.exists(compressed_dir):
                os.makedirs(compressed_dir)

            try:
                # Step 1: Compress all images first
                print(f"\n=== Step 1: Compressing images in {current_group_id} ===")
                image_files = []
                for filename in os.listdir(source_dir):
                    if not image_processor.is_valid_image(filename):
                        continue

                    input_path = os.path.join(source_dir, filename)
                    compressed_filename = filename.replace('.', '-compressed.')
                    output_path = os.path.join(compressed_dir, compressed_filename)

                    # Check if compressed version exists and is up-to-date
                    needs_compression = True
                    if os.path.exists(output_path):
                        # Compare modification times
                        input_mtime = os.path.getmtime(input_path)
                        output_mtime = os.path.getmtime(output_path)
                        if output_mtime >= input_mtime:
                            needs_compression = False
                            print(f"Using cached compressed version of {filename}")

                    # Compress image only if needed
                    if needs_compression:
                        print(f"Compressing {filename}...")
                        if not image_processor.process_image(input_path, output_path):
                            print(f"Failed to compress {filename}, skipping...")
                            continue
                        
                        # Print compression stats for newly compressed files
                        ratio, orig_mb, comp_mb = image_processor.get_compression_stats(
                            input_path, output_path
                        )
                        print(f"    Size reduced by {ratio:.1f}% ({orig_mb:.1f}MB → {comp_mb:.1f}MB)")

                    # Store file info for upload phases
                    image_files.append({
                        'filename': filename,
                        'input_path': input_path,
                        'compressed_filename': compressed_filename,
                        'output_path': output_path
                    })

                print(f"Compression complete. {len(image_files)} images ready for upload.")

                # Step 2: Upload all compressed images
                print(f"\n=== Step 2: Uploading compressed images ===")
                for file_info in image_files:
                    s3_keys = s3_uploader.get_s3_keys(
                        current_group_id, file_info['filename'], file_info['compressed_filename']
                    )
                    
                    compressed_url = s3_uploader.upload_file(
                        file_info['output_path'], s3_keys['compressed']
                    )
                    
                    if compressed_url:
                        file_info['compressed_s3_key'] = s3_keys['compressed']
                        file_info['compressed_url'] = compressed_url
                        print(f"Uploaded compressed: {file_info['filename']}")
                    else:
                        print(f"Failed to upload compressed version of {file_info['filename']}")

                # Add successfully uploaded compressed images to processed list
                for file_info in image_files:
                    if 'compressed_s3_key' in file_info:
                        processed_images.append({
                            "compressed": file_info['compressed_s3_key']
                        })

                print(f"\nUpload complete. {len(processed_images)} images successfully processed.")
                        
            except Exception as e:
                print(f"Error processing directory {source_dir}: {str(e)}")

            # Update gallery config with processed images for this directory
            if processed_images:
                gallery_manager.update_group_images(current_group_id, processed_images)
            else:
                print(f"No images were processed successfully in {source_dir}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config = os.path.join(script_dir, 'config.json')
    
    parser = argparse.ArgumentParser(description='Process and upload images to S3')
    parser.add_argument('--config', default=default_config,
                        help='Path to config file (default: config.json in script directory)')
    parser.add_argument('--group',
                        help='Optional group ID. If not provided, directory names will be used as group IDs')
    parser.add_argument('--source-dir',
                        help='Optional source directory for images')
    args = parser.parse_args()

    try:
        process_group(args.config, args.group, args.source_dir)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
