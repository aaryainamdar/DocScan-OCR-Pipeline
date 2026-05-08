# DocScan OCR Pipeline

> Built by **Aarya Inamdar** — AI/ML Student  
> A Flask-based document digitization pipeline with OpenCV preprocessing, dual-engine OCR (Tesseract + EasyOCR), and NLP post-processing.

---

## Project Structure

```
doc-scanner/
├── app.py                  ← Flask app + REST API
├── requirements.txt        ← Python dependencies
├── run.sh                  ← (Linux/macOS only — skip on Windows)
├── ocr_engine.py           ← Tesseract / EasyOCR abstraction
├── pdf_exporter.py         ← ReportLab PDF generation
├── postprocessor.py        ← NLP cleaning & entity extraction
├── preprocessor.py         ← OpenCV image preprocessing
├── templates/
│   └── index.html          ← Frontend UI
├── uploads/                ← Raw uploaded images (auto-created)
└── processed/              ← Preprocessed images + results (auto-created)
```

---

## Setup (Windows)

### Step 1 — Install Tesseract

Tesseract is an external binary that `pytesseract` wraps. It must be installed and on your PATH before running the app.

1. Download the Windows installer from:  
   👉 https://github.com/UB-Mannheim/tesseract/wiki

2. Run the installer. Note the install path — default is:  
   `C:\Program Files\Tesseract-OCR`

3. Add Tesseract to your system PATH:
   - Press `Win + S` → search **"Environment Variables"** → click **"Edit the system environment variables"**
   - Under **System Variables**, find `Path` → click **Edit**
   - Click **New** → paste: `C:\Program Files\Tesseract-OCR`
   - Click **OK** on all windows to save

4. Verify the install — open a **new** Command Prompt or PowerShell and run:
   ```cmd
   tesseract --version
   ```
   You should see version info printed. If you get `'tesseract' is not recognized`, the PATH wasn't saved correctly — restart your terminal or PC and try again.

> **Optional languages:** Download `.traineddata` files from the [tessdata repo](https://github.com/tesseract-ocr/tessdata) and drop them into `C:\Program Files\Tesseract-OCR\tessdata\`

---

### Step 2 — Navigate to the project

Open your terminal (Command Prompt, PowerShell, or the VS Code terminal):

```cmd
cd path\to\doc-scanner
```

---

### Step 3 — Create a virtual environment

```cmd
python -m venv venv
venv\Scripts\activate
```

Once activated, your prompt will show `(venv)` at the start. Always activate this before running the project.

---

### Step 4 — Install Python dependencies

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ **EasyOCR heads-up:** The first time EasyOCR runs, it downloads ~200MB of model weights. This is a one-time download and gets cached locally afterward. Don't be alarmed if the first request is slow.

---

### Step 5 — Run the application

```cmd
python app.py
```

> **Note:** `run.sh` is a Linux/macOS convenience script — ignore it on Windows.

Then open your browser at: **http://localhost:5000**

---

## Choosing Your OCR Engine

Since you're running both engines, here's a quick guide on when to use which:

| Engine     | Accuracy | Speed  | Best For                                  |
|------------|----------|--------|-------------------------------------------|
| Tesseract  | Good     | Fast   | Clean, typed documents; quick iteration   |
| EasyOCR    | Better   | Slower | Handwriting, noisy scans, complex layouts |

To switch engines, set the `ocr_engine` field in your API request:
```json
"ocr_engine": "tesseract"   // or "easyocr"
```

---

## REST API Reference

### `POST /api/upload`
Upload and process a document image.

**Form fields:**

| Field        | Type   | Default     | Description                        |
|--------------|--------|-------------|------------------------------------|
| `file`       | File   | required    | Image file (PNG, JPG, TIFF, etc.)  |
| `ocr_engine` | string | `tesseract` | `tesseract` or `easyocr`           |
| `language`   | string | `eng`       | Tesseract lang code (`eng`, `fra`) |
| `enhance`    | string | `true`      | Enable CLAHE + denoising           |

**Example response:**
```json
{
  "doc_id": "uuid",
  "status": "success",
  "processing_time_s": 1.42,
  "preprocessing": {
    "original_size": [1200, 900],
    "deskew_angle_deg": -0.8,
    "steps_applied": ["grayscale", "deskew", "perspective_transform", "denoise", "clahe_contrast", "otsu_binarization", "morphological_cleanup"]
  },
  "ocr": {
    "engine": "tesseract",
    "language": "eng",
    "confidence": 87.3,
    "raw_text": "..."
  },
  "output": {
    "cleaned_text": "...",
    "word_count": 312,
    "entities": {
      "emails": ["contact@company.com"],
      "phone_numbers": ["+1-800-555-0100"],
      "dates": ["January 12, 2024"],
      "monetary_amounts": ["$1,250.00"]
    }
  }
}
```

### Other Endpoints

| Method | Endpoint                    | Description                       |
|--------|-----------------------------|-----------------------------------|
| GET    | `/api/result/<doc_id>`      | Retrieve a cached result          |
| GET    | `/api/export/<doc_id>/json` | Download result as `.json`        |
| GET    | `/api/export/<doc_id>/pdf`  | Download formatted PDF report     |
| GET    | `/api/health`               | Health check → `{"status": "ok"}` |

---

## Pipeline Overview

```
Image Upload
    │
    ▼
Grayscale Conversion
    │
    ▼
Deskew (Hough Lines)
    │
    ▼
Perspective Transform (document boundary detection)
    │
    ▼
Denoising (fastNlMeansDenoising)
    │
    ▼
CLAHE Contrast Enhancement
    │
    ▼
Otsu Binarization
    │
    ▼
Morphological Cleanup
    │
    ▼
OCR (Tesseract or EasyOCR)
    │
    ▼
NLP Post-processing
  ├─ Unicode normalization
  ├─ OCR error correction (regex rules)
  ├─ Whitespace normalization
  ├─ Paragraph & heading detection
  └─ Entity extraction (dates, emails, phones, amounts, URLs)
    │
    ▼
JSON result + optional PDF export
```

---

## Troubleshooting (Windows)

**`'tesseract' is not recognized`**  
The PATH wasn't updated correctly. Double-check Step 1, then open a **new** terminal window. If it still fails, restart your PC.

**`venv\Scripts\activate` is blocked by PowerShell**  
Run this once to allow script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**EasyOCR is very slow on first request**  
Expected — it's downloading ~200MB of model weights. Wait it out; subsequent runs will be fast.

**Low confidence scores**  
- Make sure `enhance=true` is set in your request
- Use a scan at 300+ DPI for best results
- Try switching from Tesseract to EasyOCR for complex or noisy documents

**Perspective transform not triggering**  
The document must occupy at least 15% of the image frame and have a clear rectangular boundary against the background.

---

*Last updated by Aarya Inamdar*
