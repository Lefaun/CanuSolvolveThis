#!/bin/bash
# Pandas Build Resolver - Installation Script

echo "🐼 Installing Pandas Build Resolver..."

# Create virtual environment
python3 -m venv pandas_resolver_env
source pandas_resolver_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install requests beautifulsoup4 lxml

# Make scripts executable
chmod +x pandas_build_resolver.py
chmod +x quick_pandas_fix.py

echo "✅ Installation complete!"
echo "🔧 Usage:"
echo "   Comprehensive analysis: ./pandas_build_resolver.py --log-file your_log.txt"
echo "   Quick fix: ./quick_pandas_fix.py"
echo "   Virtual environment: source pandas_resolver_env/bin/activate"
