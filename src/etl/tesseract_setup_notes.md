# Tesseract OCR Setup Notes

## Installation Instructions

### Windows
1. Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location (usually C:\Program Files\Tesseract-OCR)
3. Add to PATH or set pytesseract.pytesseract.tesseract_cmd path

### macOS
```bash
brew install tesseract
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install tesseract-ocr
```

## Python Dependencies

### MoviePy 2.x Compatibility
This project now uses MoviePy 2.x, which has breaking changes from MoviePy 1.x:

#### Import Changes
- **Old (MoviePy 1.x):** `from moviepy.editor import VideoFileClip`
- **New (MoviePy 2.x):** `from moviepy import VideoFileClip`

#### Key Differences
- No more `moviepy.editor` module - import directly from `moviepy`
- Methods that modify clips now start with `with_` (e.g., `.with_duration()`, `.with_position()`)
- Methods like `.subclip()` are now `.subclipped()`
- Effects use `.with_effects()` and import from `moviepy.video.fx`
- Audio methods use direct multiplication for volume adjustment

#### Installation
```bash
pip install moviepy>=2.0.0
```

### Other Dependencies
```bash
pip install pytesseract>=0.3.10
pip install pillow>=8.0.0
pip install yt-dlp>=2024.3.10
```

## Configuration

### Tesseract Path Configuration
If tesseract is not in your PATH, you may need to configure it in Python:

```python
import pytesseract
# Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# macOS/Linux (if not in PATH)
pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
```

## Usage Examples

### Basic OCR
```python
from PIL import Image
import pytesseract

# Simple OCR
image = Image.open('text_image.png')
text = pytesseract.image_to_string(image)
print(text)
```

### With Custom Config
```python
custom_config = r'--oem 3 --psm 6'
text = pytesseract.image_to_string(image, config=custom_config)
```

### Video Frame Processing (MoviePy 2.x)
```python
from moviepy import VideoFileClip
from PIL import Image
import pytesseract

# Extract frames and perform OCR
video = VideoFileClip('video.mp4')
frame = video.get_frame(5)  # Get frame at 5 seconds
image = Image.fromarray(frame)
text = pytesseract.image_to_string(image)
video.close()  # Always close to free resources
```

## Troubleshooting

### Common Issues

1. **"TesseractNotFoundError"**
   - Solution: Install Tesseract OCR or add to PATH
   - Or set `pytesseract.pytesseract.tesseract_cmd`

2. **Poor OCR Quality**
   - Solution: Use appropriate `--psm` (Page Segmentation Mode)
   - Common values: 6 (uniform block), 8 (single word), 13 (raw line)

3. **MoviePy Import Errors**
   - Solution: Ensure MoviePy 2.x is installed
   - Use `from moviepy import VideoFileClip` (not `from moviepy.editor`)

4. **Memory Issues with Large Videos**
   - Solution: Process frames in smaller batches
   - Use `video.close()` to free memory after processing

## Performance Tips

1. **Limit Frame Processing**: Don't process every frame, use intervals
2. **Use Lower Quality Videos**: For OCR, video quality can be reduced
3. **Add Processing Delays**: Be respectful to system resources
4. **Clean Up Resources**: Always close video clips after use

## Language Support

Tesseract supports many languages. Install additional language packs:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr-spa  # Spanish
sudo apt-get install tesseract-ocr-fra  # French

# macOS
brew install tesseract-lang
```

Use in Python:
```python
text = pytesseract.image_to_string(image, lang='spa')  # Spanish
text = pytesseract.image_to_string(image, lang='eng+spa')  # English + Spanish
```
