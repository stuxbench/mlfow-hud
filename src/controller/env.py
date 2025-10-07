"""Environment management for MLFlow vulnerability testing."""
import sys
import asyncio
import logging

# Add shared code to path
sys.path.insert(0, '/donotaccess')

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s'
)

def setup_environment():
    """Set up MLFlow environment."""
    
    logging.info("Environment initialized for MLFlow CVE-2025-99999")

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