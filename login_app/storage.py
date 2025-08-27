import os
from datetime import datetime
from werkzeug.utils import secure_filename
from .extensions import get_supabase

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def upload_file(file, bucket, prefix='', allowed_extensions=None):
    """
    Upload a file to Supabase Storage
    
    Args:
        file: FileStorage object from request.files
        bucket: Name of the bucket to upload to
        prefix: Optional prefix for the filename
        allowed_extensions: Set of allowed file extensions
        
    Returns:
        str: Public URL of the uploaded file or None if upload failed
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename, allowed_extensions):
        return None
    
    try:
        # Generate a unique filename
        timestamp = int(datetime.utcnow().timestamp())
        filename = secure_filename(file.filename)
        filename = f"{prefix}{timestamp}_{filename}"
        
        # Upload to Supabase Storage
        supabase = get_supabase()
        
        # Read file data
        file_data = file.read()
        
        # Upload file
        response = supabase.storage.from_(bucket).upload(
            file=file_data,
            path=filename,
            file_options={"content-type": file.content_type}
        )
        
        if response.get('error'):
            raise Exception(response['error'])
        
        # Get public URL
        response = supabase.storage.from_(bucket).get_public_url(filename)
        return response.public_url
        
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return None

def delete_file(filename, bucket):
    """
    Delete a file from Supabase Storage
    
    Args:
        filename: Name of the file to delete (without bucket path)
        bucket: Name of the bucket
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        if not filename or filename == 'default.jpg':
            return True
            
        supabase = get_supabase()
        response = supabase.storage.from_(bucket).remove([filename])
        
        if response.get('error'):
            raise Exception(response['error'])
            
        return True
        
    except Exception as e:
        print(f"Error deleting file: {str(e)}")
        return False
