#!/usr/bin/env python3
"""
Quick setup script for YouTube Transcript Processor
This script helps users set up the project quickly with guided configuration.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🎬 YouTube Transcript Processor - Setup Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    if sys.version_info < (3, 9):
        print("❌ Error: Python 3.9 or higher is required.")
        print(f"   Current version: {sys.version}")
        print("   Please upgrade Python and try again.")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"✅ FFmpeg found at: {ffmpeg_path}")
        return True
    else:
        print("⚠️  FFmpeg not found in PATH")
        print("   Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
        return False

def create_virtual_environment():
    """Create and activate virtual environment"""
    if not os.path.exists("venv"):
        print("📦 Creating virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("✅ Virtual environment already exists")
    return True

def install_requirements():
    """Install Python dependencies"""
    venv_python = "venv/bin/python" if os.name != "nt" else "venv\\Scripts\\python"
    venv_pip = "venv/bin/pip" if os.name != "nt" else "venv\\Scripts\\pip"
    
    if not os.path.exists(venv_python):
        print("❌ Virtual environment not found. Please create it first.")
        return False
    
    print("📚 Installing Python dependencies...")
    try:
        subprocess.run([venv_pip, "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def setup_config_files():
    """Set up configuration files from examples"""
    files_to_setup = [
        ("config.yaml.example", "config.yaml"),
        (".env.example", ".env")
    ]
    
    for example_file, target_file in files_to_setup:
        if not os.path.exists(target_file):
            if os.path.exists(example_file):
                shutil.copy2(example_file, target_file)
                print(f"✅ Created {target_file} from {example_file}")
            else:
                print(f"⚠️  {example_file} not found")
        else:
            print(f"✅ {target_file} already exists")

def create_directories():
    """Create necessary directories"""
    directories = ["logs", "channels"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def print_next_steps():
    """Print instructions for next steps"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete! Next Steps:")
    print("=" * 60)
    print()
    print("1. 🔑 Configure API Keys:")
    print("   Edit .env file and add:")
    print("   - OPENAI_API_KEY=your_openai_api_key")
    print("   - GOOGLE_APPLICATION_CREDENTIALS=./google.json")
    print()
    print("2. 📋 Configure Channels:")
    print("   Edit config.yaml and add your YouTube channel usernames")
    print()
    print("3. 🔐 Add Google Cloud Credentials:")
    print("   - Download service account JSON from Google Cloud Console")
    print("   - Save it as 'google.json' in the project root")
    print("   - Enable Text-to-Speech and Drive APIs")
    print()
    print("4. 🚀 Run the Application:")
    print("   source venv/bin/activate  # Activate virtual environment")
    print("   python new_main.py        # Run the processor")
    print()
    print("📚 For detailed instructions, see README.md")
    print("🐛 For issues, see CONTRIBUTING.md")

def main():
    """Main setup function"""
    print_header()
    
    # Check prerequisites
    check_python_version()
    ffmpeg_available = check_ffmpeg()
    
    # Setup steps
    if not create_virtual_environment():
        print("❌ Setup failed at virtual environment creation")
        sys.exit(1)
    
    if not install_requirements():
        print("❌ Setup failed at dependency installation")
        sys.exit(1)
    
    setup_config_files()
    create_directories()
    
    # Final status
    print("\n" + "✅" * 20)
    print("Setup completed successfully!")
    
    if not ffmpeg_available:
        print("\n⚠️  Note: FFmpeg is not installed. Audio processing will not work.")
        print("   Install it before running the application.")
    
    print_next_steps()

if __name__ == "__main__":
    main()
