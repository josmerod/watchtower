# Tesseract OCR Engine Setup

The YouTube Shorts OCR ETL (`youtube_shorts_ocr_etl.py`) uses `pytesseract` to perform Optical Character Recognition (OCR) on video frames. `pytesseract` is a Python wrapper for Google's Tesseract OCR Engine.

**You MUST install Tesseract OCR Engine on your system for the OCR functionality to work.**

## Installation Instructions:

### Windows
- Download the installer from the official Tesseract at UB Mannheim page: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- During installation, make sure to add Tesseract to your system PATH.
- You might need to specify the path to `tesseract.exe` in your Python script if it's not found automatically, e.g.:
  `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`

### macOS
- You can install Tesseract using Homebrew:
  `brew install tesseract`
- You may also need to install language packs:
  `brew install tesseract-lang`

### Linux (Debian/Ubuntu)
- Install Tesseract using apt:
  `sudo apt update`
  `sudo apt install tesseract-ocr`
- Install language packs (e.g., for English):
  `sudo apt install tesseract-ocr-eng`
- For other distributions, use your respective package manager (e.g., `yum`, `dnf`).

### Docker
If you are running this project in a Docker container, ensure Tesseract is installed in your Dockerfile. For example, on a Debian-based image:
```Dockerfile
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng
```

## Verifying Installation
After installation, you can try running `tesseract --version` in your terminal to confirm it's installed and accessible via your PATH.

If `pytesseract` still cannot find Tesseract, you might need to set the `TESSDATA_PREFIX` environment variable to point to your Tesseract installation's `tessdata` directory.

---

**Note:** The OCR quality depends on the video resolution, clarity of text, fonts used, and installed language data for Tesseract.
