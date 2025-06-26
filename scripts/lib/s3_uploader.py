"""S3 upload functionality for image processing."""
import boto3
from typing import Dict, Optional
from datetime import datetime

class S3Uploader:
    def __init__(self, config: Dict):
        """Initialize S3 uploader with configuration."""
        self.config = config
        self.s3 = boto3.client('s3', region_name=config['region'])

    def upload_file(self, file_path: str, s3_key: str) -> Optional[str]:
        """Upload a file to S3 and return its URL."""
        try:
            self.s3.upload_file(
                file_path,
                self.config['bucket'],
                s3_key
            )
            return f"https://{self.config['bucket']}.s3.amazonaws.com/{s3_key}"
        except Exception as e:
            print(f"Error uploading {file_path} to S3: {str(e)}")
            return None

    def get_s3_keys(self, group_id: str, filename: str, compressed_filename: str) -> Dict[str, str]:
        """Generate S3 keys for original and compressed images."""
        timestamp = datetime.now().strftime('%Y%m%d')
        s3_prefix = f"{self.config['base_path']}/{group_id}/{timestamp}"
        
        return {
            'original': f"{s3_prefix}/original/{filename}",
            'compressed': f"{s3_prefix}/compressed/{compressed_filename}"
        }
