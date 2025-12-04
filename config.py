"""
Configuration management for Uni Helper
Loads environment variables and provides configuration access
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""

    # Gmail Configuration
    GMAIL_EMAIL = os.getenv('GMAIL_EMAIL', '')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')

    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'claude').lower()
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    # Local Model Configuration (for AI_PROVIDER='local')
    LOCAL_MODEL_PATH = os.getenv('LOCAL_MODEL_PATH', './models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf')
    LOCAL_MODEL_THREADS = int(os.getenv('LOCAL_MODEL_THREADS', 4))

    # Application Settings
    POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 60))  # seconds
    REMINDER_TIME = os.getenv('REMINDER_TIME', '09:00')  # HH:MM format
    REMINDER_HOURS_BEFORE = int(os.getenv('REMINDER_HOURS_BEFORE', 24))

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/unihelper.db')

    # Deployment
    PORT = int(os.getenv('PORT', 8080))
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        errors = []

        if not cls.GMAIL_EMAIL:
            errors.append("GMAIL_EMAIL is not set")

        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD is not set")

        if cls.AI_PROVIDER == 'claude' and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set (AI_PROVIDER is 'claude')")

        if cls.AI_PROVIDER == 'openai' and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set (AI_PROVIDER is 'openai')")

        if cls.AI_PROVIDER == 'local':
            if not cls.LOCAL_MODEL_PATH:
                errors.append("LOCAL_MODEL_PATH is not set (AI_PROVIDER is 'local')")
        elif cls.AI_PROVIDER not in ['claude', 'openai']:
            errors.append(f"AI_PROVIDER must be 'claude', 'openai', or 'local', got '{cls.AI_PROVIDER}'")

        return errors

    @classmethod
    def is_configured(cls):
        """Check if the application is properly configured"""
        return len(cls.validate()) == 0

    @classmethod
    def print_status(cls):
        """Print configuration status (without exposing sensitive data)"""
        print("=" * 60)
        print("Configuration Status")
        print("=" * 60)
        print(f"Gmail Email: {'✓ Set' if cls.GMAIL_EMAIL else '✗ Not set'}")
        print(f"Gmail App Password: {'✓ Set' if cls.GMAIL_APP_PASSWORD else '✗ Not set'}")
        print(f"AI Provider: {cls.AI_PROVIDER}")

        if cls.AI_PROVIDER == 'claude':
            print(f"Anthropic API Key: {'✓ Set' if cls.ANTHROPIC_API_KEY else '✗ Not set'}")
        elif cls.AI_PROVIDER == 'openai':
            print(f"OpenAI API Key: {'✓ Set' if cls.OPENAI_API_KEY else '✗ Not set'}")
        else:
            print(f"Local Model Path: {cls.LOCAL_MODEL_PATH or '✗ Not set'}")
            print(f"Local Model Threads: {cls.LOCAL_MODEL_THREADS}")

        print(f"Poll Interval: {cls.POLL_INTERVAL}s")
        print(f"Reminder Time: {cls.REMINDER_TIME}")
        print(f"Reminder Hours Before: {cls.REMINDER_HOURS_BEFORE}")
        print(f"Database Path: {cls.DATABASE_PATH}")
        print(f"Environment: {cls.ENVIRONMENT}")
        print("=" * 60)

        # Validation errors
        errors = cls.validate()
        if errors:
            print("\n⚠️  Configuration Errors:")
            for error in errors:
                print(f"  - {error}")
            print("\n💡 Please copy .env.template to .env and fill in your credentials")
        else:
            print("\n✓ Configuration is valid!")
        print("=" * 60)


if __name__ == "__main__":
    # Test configuration
    Config.print_status()
