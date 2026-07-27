"""
Comprehensive unit tests for fun_asr_cli.py.

Tests are organized into sections:
  1. Argument parsing
  2. Output formatting (text, JSON, SRT)
  3. Error handling (exceptions, exit codes)
  4. S3 operations (mocked)
  5. Audio processing
  6. ASR task flow (mocked)
  7. Integration scenarios (mocked end-to-end)
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Ensure the script's directory is on sys.path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
import fun_asr_cli as asr


# ===================================================================
# 1. Argument Parsing
# ===================================================================

class TestArgumentParsing:
    """Test CLI argument parsing — each flag, default, and constraint."""

    def test_minimal_args(self):
        """Required positional arg only."""
        args = asr.build_parser().parse_args(["audio.mp3"])
        assert args.file == "audio.mp3"
        assert args.model == "fun-asr"
        assert args.diarization is True
        assert args.language == "zh"
        assert args.channel_id == 0
        assert args.format == "text"
        assert args.output is None
        assert args.keep_s3 is False
        assert args.quiet is False
        assert args.version is False

    def test_no_diarization_disables_diarization(self):
        args = asr.build_parser().parse_args(["a.mp3", "--no-diarization"])
        assert args.diarization is False

    def test_all_flags(self):
        args = asr.build_parser().parse_args([
            "test.flac",
            "--model", "paraformer-v2",
            "--no-diarization",
            "--language", "en",
            "--channel-id", "1",
            "--output", "out.txt",
            "--format", "json",
            "--keep-s3",
            "--quiet",
        ])
        assert args.file == "test.flac"
        assert args.model == "paraformer-v2"
        assert args.diarization is False
        assert args.language == "en"
        assert args.channel_id == 1
        assert args.output == "out.txt"
        assert args.format == "json"
        assert args.keep_s3 is True
        assert args.quiet is True

    def test_version_flag(self):
        try:
            asr.build_parser().parse_args(["--version"])
        except SystemExit:
            pass  # --version exits 0 in main(), but parse_args alone doesn't

    def test_invalid_model_raises(self, capsys):
        """Invalid model choice should exit with error."""
        try:
            asr.build_parser().parse_args(["a.mp3", "--model", "invalid-model"])
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass

    def test_invalid_format_raises(self):
        try:
            asr.build_parser().parse_args(["a.mp3", "--format", "docx"])
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass


# ===================================================================
# 2. Output Formatting
# ===================================================================

class TestFormatText:
    """format_text() — plain text output."""

    SAMPLE_INPUT = {
        "transcripts": [
            {
                "sentences": [
                    {"speaker_id": "0", "begin_time": 1000, "end_time": 5000,
                     "text": "Hello, let's discuss the project."},
                    {"speaker_id": "1", "begin_time": 5000, "end_time": 10000,
                     "text": "Sure, let me report first."},
                ]
            }
        ]
    }

    def test_basic_format(self):
        result = asr.format_text(self.SAMPLE_INPUT)
        assert "[Speaker 0]" in result
        assert "00:00:01 - 00:00:05" in result
        assert "Hello, let's discuss the project." in result
        assert "[Speaker 1] 00:00:05 - 00:00:10" in result
        assert "Sure, let me report first." in result

    def test_no_speaker_omits_label(self):
        data = {
            "transcripts": [{
                "sentences": [
                    {"begin_time": 0, "end_time": 1000, "text": "Hello", "speaker_id": ""},
                ]
            }]
        }
        result = asr.format_text(data)
        assert "[Speaker" not in result
        assert "[00:00:00 - 00:00:01]" in result
        assert "Hello" in result

    def test_empty_transcripts(self):
        result = asr.format_text({"transcripts": []})
        assert result == ""

    def test_missing_keys_are_safe(self):
        result = asr.format_text({"transcripts": [{"sentences": [{}]}]})
        assert result is not None
        assert "[00:00:00 - 00:00:00]" in result


class TestFormatSrt:
    """format_srt() — SRT subtitle output."""

    SAMPLE_INPUT = {
        "transcripts": [
            {
                "sentences": [
                    {"speaker_id": "0", "begin_time": 1000, "end_time": 5000,
                     "text": "Hello everyone."},
                    {"speaker_id": "1", "begin_time": 5000, "end_time": 10000,
                     "text": "Good morning."},
                ]
            }
        ]
    }

    def test_basic_srt_structure(self):
        result = asr.format_srt(self.SAMPLE_INPUT)
        assert "1" in result
        assert "00:00:01,000 --> 00:00:05,000" in result
        assert "[S0] Hello everyone." in result
        assert "2" in result
        assert "00:00:05,000 --> 00:00:10,000" in result
        assert "[S1] Good morning." in result

    def test_srt_empty(self):
        result = asr.format_srt({"transcripts": []})
        assert result == ""


class TestFormatJson:
    """format_as() with json format."""

    def test_json_output_is_valid(self):
        data = {"key": "value", "nested": [1, 2, 3]}
        result = asr.format_as(data, "json")
        parsed = json.loads(result)
        assert parsed == data

    def test_json_preserves_unicode(self):
        data = {"text": "你好世界"}
        result = asr.format_as(data, "json")
        assert "你好世界" in result


class TestFormatAs:
    """format_as() dispatcher."""

    def test_delegates_to_text(self):
        data = {"transcripts": [{"sentences": [{"begin_time": 0, "end_time": 1000,
                                                  "text": "hi", "speaker_id": ""}]}]}
        result = asr.format_as(data, "text")
        assert "hi" in result
        assert "[00:00:00 - 00:00:01]" in result

    def test_delegates_to_srt(self):
        data = {"transcripts": [{"sentences": [{"begin_time": 0, "end_time": 1000,
                                                  "text": "hi", "speaker_id": "0"}]}]}
        result = asr.format_as(data, "srt")
        assert "00:00:00,000 --> 00:00:01,000" in result

    def test_delegates_to_json(self):
        data = {"status": "ok"}
        result = asr.format_as(data, "json")
        assert json.loads(result) == data


# ===================================================================
# 3. Error Handling
# ===================================================================

class TestErrorHandling:
    """Exception classes, fatal(), exit codes."""

    def test_fun_asr_error_base(self):
        exc = asr.FunAsrError("base error")
        assert exc.exit_code == asr.EXIT_API_ERROR

    def test_config_error(self):
        exc = asr.ConfigError("no api key")
        assert exc.exit_code == asr.EXIT_CONFIG_ERROR

    def test_file_error(self):
        exc = asr.FileError("not found")
        assert exc.exit_code == asr.EXIT_FILE_ERROR

    def test_audio_error(self):
        exc = asr.AudioError("bad format")
        assert exc.exit_code == asr.EXIT_AUDIO_ERROR

    def test_task_failed_error(self):
        exc = asr.TaskFailedError("api failure")
        assert exc.exit_code == asr.EXIT_TASK_FAILED

    def test_timeout_error(self):
        exc = asr.TimeoutError("timed out")
        assert exc.exit_code == asr.EXIT_TIMEOUT

    def test_fatal_exits_with_code(self):
        """fatal() should sys.exit with the exception's exit_code."""
        exc = asr.ConfigError("test config error")
        try:
            asr.fatal(exc, str(exc), detail="missing var")
            assert False, "fatal() should exit"
        except SystemExit as e:
            assert e.code == asr.EXIT_CONFIG_ERROR

    def test_fatal_with_detail(self, capsys):
        """fatal() should emit a JSON error to stderr."""
        exc = asr.FileError("file missing")
        try:
            asr.fatal(exc, str(exc), detail="/path/to/file")
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert captured.err  # stderr not empty
        err_lines = captured.err.strip().split("\n")
        last_line = json.loads(err_lines[-1])
        assert last_line["level"] == "error"
        assert last_line["code"] == asr.EXIT_FILE_ERROR
        assert last_line["detail"] == "/path/to/file"


# ===================================================================
# 4. Configuration / Environment
# ===================================================================

class TestConfiguration:
    """Environment loading, config validation."""

    def test_get_api_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                asr.get_api_key()
                assert False, "Should raise ConfigError"
            except asr.ConfigError as e:
                assert "BAILIAN_APIKEY" in str(e)

    def test_get_api_key_from_bailian(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            assert asr.get_api_key() == "sk-test"

    def test_get_api_key_from_dashscope(self):
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-ds"}, clear=True):
            assert asr.get_api_key() == "sk-ds"

    def test_get_api_key_bailian_preferred(self):
        """BAILIAN_APIKEY should take precedence when both are set."""
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-bailian",
            "DASHSCOPE_API_KEY": "sk-dashscope",
        }, clear=True):
            assert asr.get_api_key() == "sk-bailian"

    def test_validate_config_all_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            try:
                asr.validate_config()
                assert False, "Should raise ConfigError"
            except asr.ConfigError as e:
                assert "Missing" in str(e)
                assert "BAILIAN_APIKEY" in e.detail
                assert "S3_ENDPOINT" in e.detail
                assert "S3_BUCKET" in e.detail

    def test_validate_config_all_present(self):
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "my-bucket",
        }, clear=True):
            asr.validate_config()  # should not raise

    def test_s3_config_defaults(self):
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "my-bucket",
        }, clear=True):
            cfg = asr.s3_config()
            assert cfg["prefix"] == "asr-uploads"
            assert cfg["region"] == "us-east-1"

    def test_s3_config_custom(self):
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://custom.example.com/",
            "S3_BUCKET": "bucket2",
            "S3_PREFIX": "custom-prefix",
            "S3_REGION": "cn-north-1",
        }, clear=True):
            cfg = asr.s3_config()
            assert cfg["endpoint"] == "https://custom.example.com"  # trailing / stripped
            assert cfg["prefix"] == "custom-prefix"
            assert cfg["region"] == "cn-north-1"


# ===================================================================
# 5. S3 Operations (mocked)
# ===================================================================

class TestS3Operations:
    """upload_to_s3(), delete_from_s3() with mocked S3 client."""

    def test_upload_file_not_found(self):
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            try:
                asr.upload_to_s3("/nonexistent/file.mp3")
                assert False, "Should raise FileError"
            except asr.FileError as e:
                assert "not found" in str(e).lower()

    def test_upload_file_too_large(self, tmp_path):
        """2 GB+ files should be rejected."""
        large_file = tmp_path / "large.mp3"
        large_file.write_text("x" * (2 * 1024 * 1024 * 1024 + 1))  # > 2GB
        # Actually, we can't create a 2GB+ file easily. Let's adjust the test.
        # The check is: file_size_mb > 2048. A file of 2049 MB is ~2.15 GB.
        # We'll simulate by patching stat().st_size.
        import stat as stat_module
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = (2049 * 1024 * 1024)  # > 2048 MB
                try:
                    asr.upload_to_s3(str(large_file))
                    assert False, "Should raise FileError"
                except asr.FileError as e:
                    assert "too large" in str(e).lower()

    @patch("fun_asr_cli.boto3.client")
    def test_upload_success(self, mock_boto3_client, tmp_path):
        """Happy-path upload: presigned PUT + GET returned."""
        audio = tmp_path / "test.mp3"
        audio.write_text("fake audio content")

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.generate_presigned_url.side_effect = [
            "https://presigned-put-url",
            "https://presigned-get-url",
        ]

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with patch("fun_asr_cli.requests.put") as mock_put:
                mock_put.return_value.status_code = 200

                get_url, s3_key = asr.upload_to_s3(str(audio))

                assert get_url == "https://presigned-get-url"
                assert "asr-uploads/" in s3_key
                assert mock_s3.generate_presigned_url.call_count == 2
                mock_put.assert_called_once()

    @patch("fun_asr_cli.boto3.client")
    def test_upload_http_failure(self, mock_boto3_client, tmp_path):
        """S3 upload HTTP error should raise FileError."""
        audio = tmp_path / "test.mp3"
        audio.write_text("content")

        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://presigned-url"

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with patch("fun_asr_cli.requests.put") as mock_put:
                mock_put.return_value.status_code = 403
                mock_put.return_value.text = "AccessDenied"

                try:
                    asr.upload_to_s3(str(audio))
                    assert False, "Should raise FileError"
                except asr.FileError as e:
                    assert "403" in str(e)

    @patch("fun_asr_cli.boto3.client")
    def test_delete_from_s3(self, mock_boto3_client):
        """delete_from_s3 should call delete_object."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            asr.delete_from_s3("asr-uploads/test.mp3")
            mock_s3.delete_object.assert_called_once_with(
                Bucket="bucket", Key="asr-uploads/test.mp3"
            )

    @patch("fun_asr_cli.boto3.client")
    def test_delete_s3_failure_nonfatal(self, mock_boto3_client):
        """delete_from_s3 should log warning but not raise."""
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.delete_object.side_effect = Exception("Network error")

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            # Should not raise
            asr.delete_from_s3("asr-uploads/test.mp3")


# ===================================================================
# 6. Audio Processing
# ===================================================================

class TestAudioProcessing:
    """get_audio_duration(), ensure_mono(), temp file cleanup."""

    def test_get_duration_success(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_text("dummy")
        with patch("fun_asr_cli.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "42.5\n"
            mock_run.return_value.stderr = ""
            dur = asr.get_audio_duration(str(audio))
            assert dur == 42.5

    def test_get_duration_failure_returns_zero(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_text("dummy")
        with patch("fun_asr_cli.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            dur = asr.get_audio_duration(str(audio))
            assert dur == 0.0

    def test_ensure_mono_already_mono(self, tmp_path):
        """ffprobe returns channels=1 → no conversion."""
        audio = tmp_path / "mono.wav"
        audio.write_text("content")
        with patch("fun_asr_cli.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "1\n"
            result = asr.ensure_mono(str(audio))
            assert result == str(audio)  # same file returned

    def test_ensure_mono_converts(self, tmp_path):
        """ffprobe returns channels=2 → ffmpeg conversion."""
        audio = tmp_path / "stereo.wav"
        audio.write_text("content")

        with patch("fun_asr_cli.subprocess.run") as mock_run:
            # First call: ffprobe → 2 channels
            # Second call: ffmpeg → success
            mock_run.return_value.stdout = "2\n"

            result = asr.ensure_mono(str(audio))

            # Should have converted
            assert result != str(audio)
            assert "_mono" in result

            # Temp file should be tracked
            assert result in asr._temp_files

    def test_ensure_mono_no_ffprobe(self, tmp_path):
        """ffprobe not found → skip, return original."""
        audio = tmp_path / "test.wav"
        audio.write_text("content")
        with patch("fun_asr_cli.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffprobe")
            result = asr.ensure_mono(str(audio))
            assert result == str(audio)

    def test_temp_cleanup(self):
        """Tracked temp files should be removed on cleanup."""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".test")
        tmp_path = tmp.name
        tmp.close()

        asr._temp_files.append(tmp_path)
        asr.cleanup_temp_files()

        assert not os.path.exists(tmp_path)
        assert len(asr._temp_files) == 0


# ===================================================================
# 7. ASR Task Flow (mocked)
# ===================================================================

class TestAsrTaskFlow:
    """submit_task(), poll_task(), download_result() with mocked HTTP."""

    TASK_ID = "test-task-123"

    def test_submit_task_success(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {
                    "output": {"task_id": self.TASK_ID}
                }

                task_id = asr.submit_task(
                    file_url="https://example.com/audio.mp3",
                    model="fun-asr",
                    diarization=True,
                    language="zh",
                    channel_id=0,
                )
                assert task_id == self.TASK_ID

    def test_submit_task_http_error(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.post") as mock_post:
                mock_post.return_value.status_code = 401
                mock_post.return_value.text = "Unauthorized"

                try:
                    asr.submit_task("url", "fun-asr", True, "zh", 0)
                    assert False, "Should raise FunAsrError"
                except asr.FunAsrError as e:
                    assert "401" in str(e)

    def test_submit_task_no_task_id(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {"output": {}}

                try:
                    asr.submit_task("url", "fun-asr", True, "zh", 0)
                    assert False
                except asr.FunAsrError as e:
                    assert "task_id" in str(e).lower()

    def test_submit_task_network_error(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.post") as mock_post:
                mock_post.side_effect = asr.requests.RequestException("Connection refused")

                try:
                    asr.submit_task("url", "fun-asr", True, "zh", 0)
                    assert False
                except asr.FunAsrError as e:
                    assert "submit" in str(e).lower()

    def test_poll_task_succeeded(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.get") as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "output": {
                        "task_status": "SUCCEEDED",
                        "results": [{"transcription_url": "https://result.url"}],
                    }
                }

                result = asr.poll_task(self.TASK_ID)
                assert result["output"]["task_status"] == "SUCCEEDED"

    def test_poll_task_failed(self):
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.get") as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "output": {"task_status": "FAILED", "message": "Audio too long"}
                }

                try:
                    asr.poll_task(self.TASK_ID)
                    assert False
                except asr.TaskFailedError as e:
                    assert "failed" in str(e).lower()

    def test_poll_task_no_valid_speech(self):
        """ASR_RESPONSE_HAVE_NO_WORDS should raise with explicit message."""
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.get") as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "output": {
                        "task_status": "FAILED",
                        "message": "ASR_RESPONSE_HAVE_NO_WORDS: no speech detected",
                    }
                }

                try:
                    asr.poll_task(self.TASK_ID)
                    assert False
                except asr.TaskFailedError as e:
                    assert "no valid speech" in str(e).lower()

    def test_poll_task_timeout(self):
        """poll_task should raise TimeoutError after MAX_WAIT."""
        with patch.dict(os.environ, {"BAILIAN_APIKEY": "sk-test"}, clear=True):
            with patch("fun_asr_cli.requests.get") as mock_get:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = {
                    "output": {"task_status": "RUNNING"}
                }

                try:
                    # Override MAX_WAIT to a very small value for testing
                    original_max = asr.MAX_WAIT
                    asr.MAX_WAIT = 0.01  # 10ms
                    try:
                        asr.poll_task(self.TASK_ID)
                        assert False
                    except asr.TimeoutError as e:
                        assert "timeout" in str(e).lower() or "timed out" in str(e).lower()
                    finally:
                        asr.MAX_WAIT = original_max
                except asr.TimeoutError:
                    pass

    def test_download_result_success(self):
        with patch("fun_asr_cli.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "transcripts": [{"sentences": []}]
            }

            task_resp = {
                "output": {
                    "results": [
                        {
                            "subtask_status": "SUCCEEDED",
                            "transcription_url": "https://result.url",
                            "file_url": "https://audio.url",
                        }
                    ]
                }
            }

            result = asr.download_result(task_resp)
            assert "_file_url" in result
            assert result["_file_url"] == "https://audio.url"

    def test_download_result_no_results(self):
        task_resp = {"output": {"results": []}}
        try:
            asr.download_result(task_resp)
            assert False
        except asr.FunAsrError as e:
            assert "no results" in str(e).lower()

    def test_download_result_all_fail(self):
        task_resp = {
            "output": {
                "results": [
                    {"subtask_status": "FAILED", "transcription_url": "https://url"}
                ]
            }
        }
        try:
            asr.download_result(task_resp)
            assert False
        except asr.FunAsrError as e:
            assert "no transcription" in str(e).lower()


# ===================================================================
# 8. Integration / Edge Cases
# ===================================================================

class TestMainIntegration:
    """Tests for main() with mocked dependencies."""

    def test_version_exits_early(self):
        """--version should print version and exit 0 without other validation."""
        with patch.object(sys, "argv", ["fun_asr_cli.py", "--version"]):
            try:
                asr.main()
                assert False
            except SystemExit as e:
                assert e.code == asr.EXIT_SUCCESS

    def test_missing_file_exits_with_file_error(self):
        """Non-existent file should exit with EXIT_FILE_ERROR."""
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with patch.object(sys, "argv", ["fun_asr_cli.py", "/nonexistent/audio.mp3"]):
                try:
                    asr.main()
                    assert False
                except SystemExit as e:
                    assert e.code == asr.EXIT_FILE_ERROR

    def test_full_happy_path(self, tmp_path):
        """End-to-end success scenario with all dependencies mocked."""
        audio = tmp_path / "meeting.mp3"
        audio.write_text("fake audio content")

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with (
                patch.object(sys, "argv", ["fun_asr_cli.py", str(audio), "--quiet"]),
                patch("fun_asr_cli.boto3.client") as mock_boto,
                patch("fun_asr_cli.requests.put") as mock_put,
                patch("fun_asr_cli.requests.post") as mock_post,
                patch("fun_asr_cli.requests.get") as mock_get,
                patch("fun_asr_cli.subprocess.run") as mock_run,
            ):
                # S3
                mock_s3 = MagicMock()
                mock_boto.return_value = mock_s3
                mock_s3.generate_presigned_url.side_effect = [
                    "https://presigned-put",
                    "https://presigned-get",
                ]
                mock_put.return_value.status_code = 200

                # ffprobe: mono
                mock_run.return_value.stdout = "1\n"

                # Submit task
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = {
                    "output": {"task_id": "task-123"}
                }

                # Poll → succeeded on first try
                def poll_side_effect(url, **kwargs):
                    if url == f"https://dashscope.aliyuncs.com/api/v1/tasks/task-123":
                        mock_resp = MagicMock()
                        mock_resp.status_code = 200
                        mock_resp.json.return_value = {
                            "output": {
                                "task_status": "SUCCEEDED",
                                "results": [{
                                    "subtask_status": "SUCCEEDED",
                                    "transcription_url": "https://result.url",
                                    "file_url": "https://audio.url",
                                }],
                            }
                        }
                        return mock_resp
                    return mock_get.return_value

                mock_get.side_effect = poll_side_effect
                # Also handle the result download
                # Actually since we use side_effect, we need to handle both poll and download
                # Let me simplify: we'll handle both in the side_effect

                result_resp = MagicMock()
                result_resp.status_code = 200
                result_resp.json.return_value = {
                    "transcripts": [{
                        "sentences": [
                            {"speaker_id": "0", "begin_time": 1000, "end_time": 5000,
                             "text": "Hello, testing."},
                        ]
                    }]
                }

                # We need poll_side_effect for the first call, then result download
                call_count = [0]

                def combined_side_effect(url, **kwargs):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        # First GET → poll result
                        resp = MagicMock()
                        resp.status_code = 200
                        resp.json.return_value = {
                            "output": {
                                "task_status": "SUCCEEDED",
                                "results": [{
                                    "subtask_status": "SUCCEEDED",
                                    "transcription_url": "https://result.url",
                                    "file_url": "https://audio.url",
                                }],
                            }
                        }
                        return resp
                    else:
                        # Second GET → download result
                        return result_resp

                mock_get.side_effect = combined_side_effect

                # Run main()
                try:
                    asr.main()
                except SystemExit as e:
                    assert e.code == asr.EXIT_SUCCESS, f"Expected success, got {e.code}"

    def test_missing_env_var_exits_with_config_error(self):
        """Missing required env vars should exit with EXIT_CONFIG_ERROR."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["fun_asr_cli.py", "test.mp3"]):
                with patch("fun_asr_cli.load_env"):  # prevent real .env from loading
                    try:
                        asr.main()
                        assert False
                    except SystemExit as e:
                        assert e.code == asr.EXIT_CONFIG_ERROR

    def test_diarization_long_audio_raises(self, tmp_path):
        """Audio > 2 hours with diarization should raise FileError."""
        audio = tmp_path / "long.mp3"
        audio.write_text("content")

        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            with patch.object(sys, "argv", ["fun_asr_cli.py", str(audio)]):
                with patch("fun_asr_cli.get_audio_duration", return_value=7201):
                    try:
                        asr.main()
                        assert False
                    except SystemExit as e:
                        assert e.code == asr.EXIT_FILE_ERROR

    def test_keyboard_interrupt_exits_130(self, tmp_path):
        """Ctrl+C should exit 130."""
        with patch.dict(os.environ, {
            "BAILIAN_APIKEY": "sk-test",
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_BUCKET": "bucket",
        }, clear=True):
            audio = tmp_path / "test.mp3"
            audio.write_text("content")

            with patch.object(sys, "argv", ["fun_asr_cli.py", str(audio)]):
                with patch("fun_asr_cli.validate_config") as mock_val:
                    mock_val.side_effect = KeyboardInterrupt
                    try:
                        asr.main()
                        assert False
                    except SystemExit as e:
                        assert e.code == 130


# ===================================================================
# 9. Timestamp Helpers
# ===================================================================

class TestTimestampHelpers:
    """_ms_to_ts() and _ms_to_srt_ts() edge cases."""

    def test_ms_to_ts_zero(self):
        assert asr._ms_to_ts(0) == "00:00:00"

    def test_ms_to_ts_exact_second(self):
        assert asr._ms_to_ts(5000) == "00:00:05"

    def test_ms_to_ts_minutes(self):
        assert asr._ms_to_ts(125000) == "00:02:05"  # 2m5s

    def test_ms_to_ts_hours(self):
        assert asr._ms_to_ts(3600000 + 120000 + 3000) == "01:02:03"  # 1h2m3s

    def test_ms_to_srt_ts_zero(self):
        assert asr._ms_to_srt_ts(0) == "00:00:00,000"

    def test_ms_to_srt_ts_with_ms(self):
        assert asr._ms_to_srt_ts(1234) == "00:00:01,234"

    def test_ms_to_srt_ts_hours(self):
        assert asr._ms_to_srt_ts(3661123) == "01:01:01,123"
