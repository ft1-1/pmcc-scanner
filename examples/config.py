"""Config for EODHD example scripts"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
API_KEY = os.getenv('EODHD_API_TOKEN', 'demo')