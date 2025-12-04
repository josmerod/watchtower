import os
import shutil

# Ensure the src directory is in the Python path
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if project_root not in sys.path:
# sys.path.append(project_root)
# The above is commented out as it might not be robust in all test runners.
# It's generally better to run tests as a module or have PYTHONPATH set up.
# For now, assuming the test runner handles path resolution or this file is moved/adjusted.

# Dynamically adjust path for tests if running from root or specific test directory
try:
    from src.etl.youtube_shorts_ocr_etl import (
        download_video,
        extract_text_from_video_frames,
        get_short_video_urls,
    )
    from src.etl.youtube_shorts_ocr_etl import main as etl_main
    from src.utils.file_system import get_project_root
except ImportError:
    # This is a fallback if the test is run in a way that src is not directly discoverable
    # This assumes the test file is in Tests/etl/ and src is a sibling of Tests/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_for_test = os.path.abspath(os.path.join(current_dir, "../../.."))
    if project_root_for_test not in sys.path:
        sys.path.insert(0, project_root_for_test)
    from src.etl.youtube_shorts_ocr_etl import (
        download_video,
        extract_text_from_video_frames,
        get_short_video_urls,
    )
    from src.etl.youtube_shorts_ocr_etl import main as etl_main
    from src.utils.file_system import get_project_root


# Define global constants for cleaner test structure
TEST_OUTPUT_DIR = os.path.join(get_project_root(), "Tests", "temp_test_output", "youtube_shorts_ocr")
TEST_TEMP_VIDEO_DIR = os.path.join(TEST_OUTPUT_DIR, "temp_videos")
TARGET_CHANNEL_URL_FOR_TEST = "https://youtube.com/@testchannel/shorts"


# Helper to clean up test directories
def cleanup_test_dirs():
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)


class TestYoutubeShortsOCRETL(unittest.TestCase):
    def setUp(self):
        cleanup_test_dirs()  # Clean before each test
        os.makedirs(TEST_TEMP_VIDEO_DIR, exist_ok=True)
        # Mock global constants in the ETL script if they are directly used by functions
        # For this ETL, constants like OUTPUT_DIR are used in main() which we will mock differently
        # or are passed as arguments.

    def tearDown(self):
        cleanup_test_dirs()  # Clean after each test

    @patch("src.etl.youtube_shorts_ocr_etl.yt_dlp.YoutubeDL")
    def test_get_short_video_urls_success(self, mock_yt_dlp):
        """Test fetching short video URLs successfully."""
        mock_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            "entries": [
                {"id": "short1", "title": "First Short"},
                {"id": "short2", "title": "Second Short"},
            ]
        }

        videos = get_short_video_urls(TARGET_CHANNEL_URL_FOR_TEST, limit=5, lookback_days=30)
        self.assertEqual(len(videos), 2)
        self.assertEqual(videos[0]["id"], "short1")
        self.assertEqual(videos[0]["title"], "First Short")
        self.assertEqual(videos[1]["url"], "https://www.youtube.com/shorts/short2")

    @patch("src.etl.youtube_shorts_ocr_etl.yt_dlp.YoutubeDL")
    def test_get_short_video_urls_no_entries(self, mock_yt_dlp):
        """Test fetching when no entries are returned."""
        mock_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {"entries": []}

        videos = get_short_video_urls(TARGET_CHANNEL_URL_FOR_TEST, limit=5, lookback_days=30)
        self.assertEqual(len(videos), 0)

    @patch("src.etl.youtube_shorts_ocr_etl.yt_dlp.YoutubeDL")
    def test_get_short_video_urls_yt_dlp_error(self, mock_yt_dlp):
        """Test fetching when yt-dlp raises an error."""
        mock_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("yt-dlp failed")

        videos = get_short_video_urls(TARGET_CHANNEL_URL_FOR_TEST, limit=5, lookback_days=30)
        self.assertEqual(len(videos), 0)

    @patch("src.etl.youtube_shorts_ocr_etl.yt_dlp.YoutubeDL")
    @patch("src.etl.youtube_shorts_ocr_etl.os.path.exists")
    def test_download_video_success(self, mock_path_exists, mock_yt_dlp):
        """Test successful video download."""
        mock_downloader_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_downloader_instance.download.return_value = None  # download() usually returns None on success

        video_id = "testvideo1"
        expected_path = os.path.join(TEST_TEMP_VIDEO_DIR, video_id, f"{video_id}.mp4")
        mock_path_exists.return_value = True  # Simulate file exists after download

        # Ensure the test specific output path is used by the download function
        # This requires download_video to accept output_path
        result_path = download_video(video_id, TEST_TEMP_VIDEO_DIR)

        self.assertEqual(result_path, expected_path)
        mock_downloader_instance.download.assert_called_once_with([f"https://www.youtube.com/shorts/{video_id}"])

    @patch("src.etl.youtube_shorts_ocr_etl.yt_dlp.YoutubeDL")
    def test_download_video_failure(self, mock_yt_dlp):
        """Test video download failure."""
        mock_downloader_instance = mock_yt_dlp.return_value.__enter__.return_value
        mock_downloader_instance.download.side_effect = Exception("Download error")

        result_path = download_video("failvideo1", TEST_TEMP_VIDEO_DIR)
        self.assertIsNone(result_path)

    @patch("src.etl.youtube_shorts_ocr_etl.VideoFileClip")
    @patch("src.etl.youtube_shorts_ocr_etl.pytesseract.image_to_string")
    @patch("src.etl.youtube_shorts_ocr_etl.Image.fromarray")
    def test_extract_text_from_video_frames_success(self, mock_fromarray, mock_image_to_string, mock_video_file_clip):
        """Test successful OCR text extraction."""
        mock_clip_instance = mock_video_file_clip.return_value
        mock_clip_instance.duration = 2  # 2 seconds long video
        mock_clip_instance.get_frame.return_value = MagicMock()  # Mock frame data (e.g. numpy array)

        mock_pil_image = MagicMock()
        mock_fromarray.return_value = mock_pil_image

        mock_image_to_string.side_effect = [
            "Hello",
            "World",
        ]  # OCR text for frame 0 and 1

        # Create a dummy video file as VideoFileClip checks for existence
        dummy_video_path = os.path.join(TEST_TEMP_VIDEO_DIR, "dummy.mp4")
        with open(dummy_video_path, "w") as f:
            f.write("dummy_content")

        text = extract_text_from_video_frames(dummy_video_path, frame_interval_seconds=1)

        self.assertEqual(text, "Hello World")  # Texts are joined with space, unique and sorted
        self.assertEqual(mock_image_to_string.call_count, 2)
        mock_video_file_clip.assert_called_once_with(dummy_video_path)

        os.remove(dummy_video_path)  # Clean up dummy file

    @patch("src.etl.youtube_shorts_ocr_etl.VideoFileClip")
    def test_extract_text_from_video_frames_video_error(self, mock_video_file_clip):
        """Test OCR when video loading fails."""
        mock_video_file_clip.side_effect = Exception("Cannot open video")

        text = extract_text_from_video_frames("path/to/nonexistent_video.mp4")
        self.assertEqual(text, "")

    @patch("src.etl.youtube_shorts_ocr_etl.get_short_video_urls")
    @patch("src.etl.youtube_shorts_ocr_etl.download_video")
    @patch("src.etl.youtube_shorts_ocr_etl.extract_text_from_video_frames")
    @patch("src.etl.youtube_shorts_ocr_etl.open", new_callable=mock_open)
    @patch("src.etl.youtube_shorts_ocr_etl.json.dump")
    @patch("src.etl.youtube_shorts_ocr_etl.shutil.rmtree")
    @patch("src.etl.youtube_shorts_ocr_etl.os.path.exists")
    @patch("src.etl.youtube_shorts_ocr_etl.os.listdir")
    def test_etl_main_flow_success(
        self,
        mock_os_listdir,
        mock_os_path_exists,
        mock_shutil_rmtree,
        mock_json_dump,
        mock_file_open,
        mock_extract_text,
        mock_download_video,
        mock_get_urls,
    ):
        """Test the main ETL flow with mocks."""
        # Configure mocks
        mock_get_urls.return_value = [
            {"id": "vid1", "title": "Video 1", "url": "url1"},
            {"id": "vid2", "title": "Video 2", "url": "url2"},
        ]

        dummy_video_path_1 = os.path.join(TEST_TEMP_VIDEO_DIR, "vid1", "vid1.mp4")
        dummy_video_path_2 = os.path.join(TEST_TEMP_VIDEO_DIR, "vid2", "vid2.mp4")

        mock_download_video.side_effect = [dummy_video_path_1, dummy_video_path_2]
        mock_extract_text.side_effect = ["OCR text for vid1", "OCR text for vid2"]

        # Mock os.path.exists for directory checks and file cleanup
        # True for initial OUTPUT_DIR and TEMP_VIDEO_DIR checks, then for video paths during cleanup
        mock_os_path_exists.side_effect = [
            True,
            True,
            True,
            True,
            True,
        ]  # General existence for dirs, then for rmtree cleanup
        mock_os_listdir.return_value = []  # For final TEMP_VIDEO_DIR cleanup check

        # Mock args for the main function
        mock_args = MagicMock()
        mock_args.limit = 5
        mock_args.days = 30

        # Patch global constants within the etl script for OUTPUT_DIR and TEMP_VIDEO_DIR
        # to point to our test directories
        with (
            patch("src.etl.youtube_shorts_ocr_etl.OUTPUT_DIR", TEST_OUTPUT_DIR),
            patch("src.etl.youtube_shorts_ocr_etl.TEMP_VIDEO_DIR", TEST_TEMP_VIDEO_DIR),
            patch(
                "src.etl.youtube_shorts_ocr_etl.TARGET_CHANNEL_URL",
                TARGET_CHANNEL_URL_FOR_TEST,
            ),
        ):
            etl_main(mock_args)

        # Assertions
        mock_get_urls.assert_called_once_with(TARGET_CHANNEL_URL_FOR_TEST, 5, 30)
        self.assertEqual(mock_download_video.call_count, 2)
        mock_download_video.assert_any_call("vid1", TEST_TEMP_VIDEO_DIR)
        mock_download_video.assert_any_call("vid2", TEST_TEMP_VIDEO_DIR)

        self.assertEqual(mock_extract_text.call_count, 2)
        mock_extract_text.assert_any_call(dummy_video_path_1, frame_interval_seconds=1)
        mock_extract_text.assert_any_call(dummy_video_path_2, frame_interval_seconds=1)

        expected_output_file = os.path.join(TEST_OUTPUT_DIR, "youtube_shorts_ocr_results.json")
        mock_file_open.assert_called_once_with(expected_output_file, "w", encoding="utf-8")

        expected_json_data = [
            {"url": "url1", "title": "Video 1", "ocr_description": "OCR text for vid1"},
            {"url": "url2", "title": "Video 2", "ocr_description": "OCR text for vid2"},
        ]
        mock_json_dump.assert_called_once_with(expected_json_data, mock_file_open(), indent=4, ensure_ascii=False)

        # Check cleanup calls for video folders
        # shutil.rmtree is called for each video's folder and then for TEMP_VIDEO_DIR
        self.assertTrue(mock_shutil_rmtree.call_count >= 2)
        mock_shutil_rmtree.assert_any_call(os.path.join(TEST_TEMP_VIDEO_DIR, "vid1"))
        mock_shutil_rmtree.assert_any_call(os.path.join(TEST_TEMP_VIDEO_DIR, "vid2"))
        # Check if TEMP_VIDEO_DIR itself was attempted to be removed
        # This depends on whether it was empty after individual video cleanups
        # For this test, it should be called for TEMP_VIDEO_DIR if mock_os_listdir returns []
        mock_shutil_rmtree.assert_any_call(TEST_TEMP_VIDEO_DIR)


if __name__ == "__main__":
    unittest.main()
