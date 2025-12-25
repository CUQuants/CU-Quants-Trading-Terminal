#!/bin/bash

# CU Quants Trading Terminal - Installation Script
# Run this from the frontend directory

echo "🚀 Installing CU Quants Trading Terminal..."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the frontend directory."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "🎯 Next steps:"
    echo "  1. Start development server: npm run dev"
    echo "  2. Open browser: http://localhost:3000"
    echo "  3. Configure API keys in Settings page"
    echo ""
    echo "📚 Documentation:"
    echo "  - README.md - Full documentation"
    echo "  - QUICKSTART.md - Quick start guide"
    echo "  - PROJECT_STRUCTURE.md - Architecture details"
    echo "  - IMPLEMENTATION_SUMMARY.md - What was built"
    echo ""
    echo "⌨️  Keyboard Shortcuts:"
    echo "  - Alt + H: Home page"
    echo "  - Alt + T: Trading page"
    echo "  - Alt + S: Settings page"
    echo ""
else
    echo ""
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
