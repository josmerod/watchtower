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

### Video frame processing
Watchtower extracts video frames with OpenCV (`cv2.VideoCapture`) rather than MoviePy.
MoviePy was removed from the runtime dependency set because its Pillow upper bound blocked
security updates to Pillow 12.x.

### Dependencies
```bash
pip install pytesseract>=0.3.10
pip install pillow>=12.2.0
pip install opencv-python>=4.8.0
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

### Video Frame Processing (OpenCV)
```python
import cv2
from PIL import Image
import pytesseract

# Extract one frame at 5 seconds and perform OCR
capture = cv2.VideoCapture("video.mp4")
capture.set(cv2.CAP_PROP_POS_MSEC, 5000)
ok, frame_bgr = capture.read()
if ok:
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    text = pytesseract.image_to_string(image)
    print(text)
capture.release()
```

## Troubleshooting

### Common Issues

1. **"TesseractNotFoundError"**
   - Solution: Install Tesseract OCR or add to PATH
   - Or set `pytesseract.pytesseract.tesseract_cmd`

2. **Poor OCR Quality**
   - Solution: Use appropriate `--psm` (Page Segmentation Mode)
   - Common values: 6 (uniform block), 8 (single word), 13 (raw line)

3. **OpenCV cannot open video**
   - Solution: Verify the file exists, is a supported video format, and ffmpeg/OpenCV codecs are available

4. **Memory Issues with Large Videos**
   - Solution: Process frames in smaller batches
   - Use `capture.release()` to free resources after processing

## Performance Tips

1. **Limit Frame Processing**: Don't process every frame, use intervals
2. **Use Lower Quality Videos**: For OCR, video quality can be reduced
3. **Add Processing Delays**: Be respectful to system resources
4. **Clean Up Resources**: Always release video captures after use

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
