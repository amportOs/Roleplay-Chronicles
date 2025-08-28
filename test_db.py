import os
import sys
import time
import psycopg2
from urllib.parse import urlparse

def test_connection():
    print("Testing database connection...")
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        return False
    
    # Parse the database URL
    try:
        parsed = urlparse(database_url)
        
        # Extract connection parameters
        dbname = parsed.path[1:]  # Remove the leading '/'
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        port = parsed.port or 5432
        
        # Add SSL parameters
        sslmode = 'require'
        
        print(f"Connecting to database: {host}:{port}/{dbname} as {user}")
        
        # Try to connect with retries
        max_retries = 5
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    sslmode=sslmode,
                    connect_timeout=10
                )
                
                # Test the connection
                with conn.cursor() as cur:
                    cur.execute('SELECT version()')
                    version = cur.fetchone()
                    print(f"Successfully connected to: {version[0]}")
                    return True
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to connect after {max_retries} attempts")
                    print(f"Error: {str(e)}")
                    return False
            
    except Exception as e:
        print(f"Error parsing database URL: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        sys.exit(0)
    else:
        sys.exit(1)
