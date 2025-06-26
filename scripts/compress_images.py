#!/usr/bin/env python3
import os
import json
import argparse
from typing import List, Dict

from lib.config import Config
from lib.image_processor import ImageProcessor
from lib.s3_uploader import S3Uploader
from lib.gallery_manager import GalleryManager

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
    """Process images for a gallery group."""
    try:
        # Initialize components
        config = Config(config_path)
        gallery_manager = GalleryManager(config.get_gallery_config_path())
        image_processor = ImageProcessor(config.get_image_processing_config())
        s3_uploader = S3Uploader(config.get_s3_config())

        # Use provided source dir or get all configured directories
        source_dirs = [source_dir] if source_dir else config.get_image_dirs()

        for source_dir in source_dirs:
            # Read directory config if it exists
            dir_config_path = os.path.join(source_dir, 'config.json')
            if not os.path.exists(dir_config_path):
                print(f"Warning: No config.json found in {source_dir}")
                continue

            try:
                with open(dir_config_path, 'r') as f:
                    dir_config = json.load(f)
            except Exception as e:
                print(f"Error reading config.json in {source_dir}: {str(e)}")
                continue

            # Use directory name as group ID if none provided
            current_group_id = group_id or os.path.basename(source_dir)

            # Create or update group with directory config metadata
            gallery_manager.create_or_update_group(
                group_id=current_group_id,
                title=dir_config.get('name', current_group_id),
                description=dir_config.get('description', ''),
            )

            processed_images = []
            # Create temporary directory for compressed images
            temp_dir = os.path.join(source_dir, 'temp_compressed')
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)

            try:
                # Process images in this directory
                for filename in os.listdir(source_dir):
                    if not image_processor.is_valid_image(filename):
                        continue

                    input_path = os.path.join(source_dir, filename)
                    compressed_filename = filename.replace('.', '-compressed.')
                    output_path = os.path.join(temp_dir, compressed_filename)

                    # Compress image
                    if image_processor.process_image(input_path, output_path):
                        # Generate S3 keys
                        s3_keys = s3_uploader.get_s3_keys(
                            current_group_id, filename, compressed_filename
                        )

                        # Upload to S3
                        original_url = s3_uploader.upload_file(
                            input_path, s3_keys['original']
                        )
                        compressed_url = s3_uploader.upload_file(
                            output_path, s3_keys['compressed']
                        )

                        if original_url and compressed_url:
                            processed_images.append({
                                "compressed": s3_keys['compressed'],
                                "original": s3_keys['original']
                            })

                            # Print compression stats
                            ratio, orig_mb, comp_mb = image_processor.get_compression_stats(
                                input_path, output_path
                            )
                            print(f"Processed {filename}:")
                            print(f"    Size reduced by {ratio:.1f}% ({orig_mb:.1f}MB → {comp_mb:.1f}MB)")
                            print(f"    Uploaded to S3: {compressed_url}")
            except Exception as e:
                print(f"Error processing directory {source_dir}: {str(e)}")
            finally:
                # Clean up temporary directory
                if os.path.exists(temp_dir):
                    for file in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, file))
                    os.rmdir(temp_dir)

            # Update gallery config with processed images for this directory
            if processed_images:
                gallery_manager.update_group_images(current_group_id, processed_images)
            else:
                print(f"No images were processed successfully in {source_dir}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Process and upload images to S3')
    parser.add_argument('--config', default='config.json',
                        help='Path to config file')
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
