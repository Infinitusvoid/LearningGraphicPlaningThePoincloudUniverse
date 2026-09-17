#include "FfmpegWriter.h"
#include "ImageRGBA.h"

#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>

#ifdef _WIN32
#define FFMPEG_POPEN _popen
#define FFMPEG_PCLOSE _pclose
#else
#define FFMPEG_POPEN popen
#define FFMPEG_PCLOSE pclose
#endif

FfmpegWriter::FfmpegWriter()
	: pipe_(nullptr)
	, width_(0)
	, height_(0)
	, fps_(0)
	, frames_written_(0)
{
}

FfmpegWriter::~FfmpegWriter()
{
	close();
}

bool FfmpegWriter::is_ffmpeg_on_path()
{
#ifdef _WIN32
	int rc = std::system("ffmpeg -version > NUL 2>&1");
#else
	int rc = std::system("ffmpeg -version > /dev/null 2>&1");
#endif
	return rc == 0;
}

bool FfmpegWriter::open(const char* filename, int width, int height, int fps)
{
	if (is_open())
	{
		std::cerr << "[FfmpegWriter] already open, close it first.\n";
		return false;
	}

	if (!filename || !filename[0])
	{
		std::cerr << "[FfmpegWriter] empty output filename.\n";
		return false;
	}

	if (width <= 0 || height <= 0 || fps <= 0)
	{
		std::cerr << "[FfmpegWriter] invalid params ("
			<< width << "x" << height << " @ " << fps << "fps).\n";
		return false;
	}

	if (!is_ffmpeg_on_path())
	{
		std::cerr << "[FfmpegWriter] ffmpeg was not found on PATH.\n"
			<< "  Install ffmpeg and make sure `ffmpeg -version` works,\n"
			<< "  then re-run. No video was written.\n";
		return false;
	}

	// Raw RGBA in, H.264 out. yuv420p keeps players (QuickTime,
	// browsers) happy. -y overwrites without asking.
	char command[1024];
	std::snprintf(
		command, sizeof(command),
		"ffmpeg -y -loglevel warning "
		"-f rawvideo -pix_fmt rgba -s %dx%d -r %d -i - "
		"-an -c:v libx264 -pix_fmt yuv420p -crf 18 "
		"-movflags +faststart \"%s\"",
		width, height, fps, filename);

	FILE* pipe = FFMPEG_POPEN(command, "wb");
	if (!pipe)
	{
		std::cerr << "[FfmpegWriter] could not open pipe to ffmpeg.\n";
		return false;
	}

	pipe_ = pipe;
	width_ = width;
	height_ = height;
	fps_ = fps;
	frames_written_ = 0;

	std::cout << "[FfmpegWriter] piping " << width << "x" << height
		<< " @ " << fps << "fps -> " << filename << "\n";

	return true;
}

bool FfmpegWriter::is_open() const
{
	return pipe_ != nullptr;
}

bool FfmpegWriter::write_frame_raw(const unsigned char* rgba_data, int data_bytes)
{
	if (!is_open())
	{
		return false;
	}

	int expected = width_ * height_ * 4;
	if (data_bytes != expected)
	{
		std::cerr << "[FfmpegWriter] frame size mismatch: got "
			<< data_bytes << " bytes, expected " << expected << ".\n";
		return false;
	}

	size_t written = std::fwrite(rgba_data, 1, size_t(expected), pipe_);
	if (written != size_t(expected))
	{
		std::cerr << "[FfmpegWriter] broken pipe after "
			<< frames_written_ << " frames (ffmpeg died?).\n";
		return false;
	}

	frames_written_++;
	return true;
}

bool FfmpegWriter::write_frame(const ImageRGBA& image)
{
	int w = ImageRGBA_::get_width(image);
	int h = ImageRGBA_::get_height(image);

	if (w != width_ || h != height_)
	{
		std::cerr << "[FfmpegWriter] image is " << w << "x" << h
			<< " but writer is " << width_ << "x" << height_ << ".\n";
		return false;
	}

	// Grab the raw bytes without a PNG round-trip and push them
	// straight into ffmpeg's stdin.
	bool ok = false;
	ImageRGBA_::readonly_raw_direct_access(
		const_cast<ImageRGBA&>(image),
		[&](int rw, int rh, const unsigned char* const data)
		{
			(void)rw;
			(void)rh;
			ok = write_frame_raw(data, rw * rh * 4);
		});

	return ok;
}

void FfmpegWriter::close()
{
	if (!is_open())
	{
		return;
	}

	std::fflush(pipe_);
	int rc = FFMPEG_PCLOSE(pipe_);
	pipe_ = nullptr;

	if (rc != 0)
	{
		std::cerr << "[FfmpegWriter] ffmpeg exited with code " << rc
			<< " (" << frames_written_ << " frames piped).\n";
	}
	else
	{
		std::cout << "[FfmpegWriter] done, " << frames_written_ << " frames.\n";
	}

	width_ = 0;
	height_ = 0;
	fps_ = 0;
}
