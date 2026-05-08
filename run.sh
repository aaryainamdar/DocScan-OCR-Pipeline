#!/bin/bash
# ─────────────────────────────────────────────────────────────
# DocScan OCR Pipeline — Setup & Run Script
# ─────────────────────────────────────────────────────────────
set -e

echo ""
echo "══════════════════════════════════════════"
echo "  DocScan OCR Pipeline — Setup"
echo "══════════════════════════════════════════"
echo ""

# 1. Create virtualenv
echo "→ Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 2. Upgrade pip
pip install --upgrade pip -q

# 3. Install Python deps
echo "→ Installing Python dependencies..."
pip install -r requirements.txt -q

# 4. Check Tesseract
echo ""
echo "→ Checking Tesseract binary..."
if command -v tesseract &> /dev/null; then
    echo "  ✓ Tesseract found: $(tesseract --version 2>&1 | head -1)"
else
    echo "  ✗ Tesseract NOT found."
    echo ""
    echo "  Install it with:"
    echo "    Ubuntu/Debian : sudo apt-get install tesseract-ocr"
    echo "    macOS         : brew install tesseract"
    echo "    Windows       : https://github.com/UB-Mannheim/tesseract/wiki"
    echo ""
fi

# 5. Create directories
mkdir -p uploads processed

echo ""
echo "══════════════════════════════════════════"
echo "  Setup complete. Starting server..."
echo "  Open: http://localhost:5000"
echo "══════════════════════════════════════════"
echo ""

# 6. Run Flask
python app.py
