"""Environment management for MinIO vulnerability testing."""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add shared code to path
sys.path.insert(0, '/app')

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s'
)

def setup_environment():
    """Set up MinIO environment variables."""
    os.environ['MINIO_ROOT_USER'] = 'admin'
    os.environ['MINIO_ROOT_PASSWORD'] = 'password'
    
    logging.info("Environment initialized for MinIO CVE-2020-11012")
    logging.info(f"MinIO version: 2020.04.10")
    logging.info(f"Vulnerability: CVE-2020-11012")
    logging.info(f"Initial state: vulnerable branch")

async def main():
    """Initialize the environment and keep it running."""
    setup_environment()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logging.info("Shutting down environment")

if __name__ == "__main__":
    asyncio.run(main())