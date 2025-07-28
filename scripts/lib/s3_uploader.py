"""S3 upload functionality for image processing."""
import boto3
from typing import Dict, Optional, List
from datetime import datetime

class S3Uploader:
    def __init__(self, config: Dict):
        """Initialize S3 uploader with configuration."""
        self.config = config
        self.s3 = boto3.client('s3', region_name=config['region'])

    def upload_file(self, file_path: str, s3_key: str) -> Optional[str]:
        """Upload a file to S3 and return its URL."""
        try:
            # Determine content type based on file extension
            content_type = 'image/jpeg'
            if s3_key.lower().endswith('.png'):
                content_type = 'image/png'
            elif s3_key.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif s3_key.lower().endswith('.webp'):
                content_type = 'image/webp'
            
            # Upload with public-read ACL and proper content type
            self.s3.upload_file(
                file_path,
                self.config['bucket'],
                s3_key,
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': content_type
                }
            )
            return f"https://{self.config['bucket']}.s3.amazonaws.com/{s3_key}"
        except Exception as e:
            print(f"Error uploading {file_path} to S3: {str(e)}")
            return None

    def delete_collection(self, prefix: str = None) -> bool:
        """Delete all objects with the specified prefix from S3 bucket.
        
        Args:
            prefix (str): S3 prefix to delete. If None, deletes entire base_path.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Use base_path if no specific prefix provided
            delete_prefix = prefix or self.config['base_path']
            
            # List all objects with the prefix
            paginator = self.s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.config['bucket'], Prefix=delete_prefix)
            
            objects_to_delete = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects_to_delete.append({'Key': obj['Key']})
            
            if not objects_to_delete:
                print(f"No objects found with prefix '{delete_prefix}' to delete.")
                return True
            
            # Delete objects in batches (S3 allows max 1000 per batch)
            batch_size = 1000
            deleted_count = 0
            
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i + batch_size]
                response = self.s3.delete_objects(
                    Bucket=self.config['bucket'],
                    Delete={'Objects': batch}
                )
                
                deleted_count += len(batch)
                if 'Errors' in response and response['Errors']:
                    print(f"Errors deleting some objects: {response['Errors']}")
                    return False
            
            print(f"Successfully deleted {deleted_count} objects from S3 with prefix '{delete_prefix}'")
            return True
            
        except Exception as e:
            print(f"Error deleting objects from S3: {str(e)}")
            return False

    def get_s3_keys(self, group_id: str, filename: str, compressed_filename: str) -> Dict[str, str]:
        """Generate S3 keys for original and compressed images."""
        s3_prefix = f"{self.config['base_path']}/{group_id}"
        
        return {
            'original': f"{s3_prefix}/original/{filename}",
            'compressed': f"{s3_prefix}/compressed/{compressed_filename}"
        }
