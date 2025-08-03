# PlasmaProject v1-1-4/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', "sk_test_51QzjNVCZzQVxtrPQ7xJA7iCDDjxOkiaH1GkLyqfPuwWzV4CDo7iEbUpCMXf3JDbmEIzPOLpkGPFHRzCi1FyYqs7700ZvWsfJUz")
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', "pk_test_51QzjNVCZzQVxtrPQbjE71T8tQHHO5WKOkZfsdtpbBlPQzKqG8txqhaLQGd2BPFQM38jnGprUGmUlJT09djX4kWhL00eyw8KFqM")
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', "sqlite:///plasma_project.db")  # Use relative path for portability
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')  # Example; adjust for your mail server
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USE_TLS = bool(int(os.getenv('MAIL_USE_TLS', 1)))
MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'test@test.com')  # Replace with your email
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'test')  # Replace with your password
