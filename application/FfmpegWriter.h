#pragma once

#include <cstdio>

// Streams raw RGBA frames straight into ffmpeg via a pipe.
// No PNG sequence, no temp files: each frame's bytes go directly
// to ffmpeg's stdin.
//
// Usage (mirrors the ImageRGBA_ style of pass-the-image):
//
//   FfmpegWriter writer;
//   if (!writer.open("out.mp4", 512, 512, 30))
//   {
//       // ffmpeg missing or bad params, message already printed.
//       return 0;
//   }
//   ImageRGBA* img = ImageRGBA_::create(512, 512);
//   for (...) { render into *img; writer.write_frame(*img); }
//   ImageRGBA_::free_image(img);
//   writer.close();
//
// Requires ffmpeg on PATH. If it is missing, open() fails
// gracefully with a message and no crash.

struct ImageRGBA;

class FfmpegWriter
{
public:
	FfmpegWriter();
	~FfmpegWriter();

	FfmpegWriter(const FfmpegWriter&) = delete;
	FfmpegWriter& operator=(const FfmpegWriter&) = delete;

	// Opens the pipe. Returns false (with a message) if ffmpeg
	// is not on PATH or the parameters are invalid.
	bool open(const char* filename, int width, int height, int fps);

	bool is_open() const;

	// Writes one frame. Image dimensions must match open().
	// Returns false on mismatch or broken pipe.
	bool write_frame(const ImageRGBA& image);

	// Raw-bytes escape hatch: pointer to width*height*4 RGBA bytes.
	// Same path write_frame(ImageRGBA) uses internally.
	bool write_frame_raw(const unsigned char* rgba_data, int data_bytes);

	void close();

	int get_width() const { return width_; }
	int get_height() const { return height_; }
	int get_fps() const { return fps_; }
	long get_frames_written() const { return frames_written_; }

	// Quick check without opening anything.
	static bool is_ffmpeg_on_path();

private:
	struct PipeCloser;
	FILE* pipe_;
	int width_;
	int height_;
	int fps_;
	long frames_written_;
};
