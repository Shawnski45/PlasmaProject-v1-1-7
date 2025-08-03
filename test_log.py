import logging

try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('error.log', encoding='utf-8')
        ]
    )
    logging.info("This is a test log entry.")
    # Force flush and shutdown to ensure log is written
    for handler in logging.getLogger().handlers:
        handler.flush()
    logging.shutdown()
    print("Test log entry written to error.log.")
except Exception as e:
    print(f"Failed to write to error.log: {e}")
