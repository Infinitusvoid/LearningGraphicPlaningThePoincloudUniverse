#include "ImageRGBA.h"
#include "Math.h"

namespace Raster_
{
	void draw_rectangle(ImageRGBA& image, int x_min, int y_min, int x_max, int y_max, RGBA color);
	
	bool clip_line_to_image(
		const ImageRGBA& image,
		float& a_x,
		float& a_y,
		float& b_x,
		float& b_y);
		
	void draw_line(
		ImageRGBA& image,
		int a_x,
		int a_y,
		int b_x,
		int b_y,
		RGBA color);
		
	void draw_triangle_wireframe(
		ImageRGBA& image,
		int a_x, int a_y,
		int b_x, int b_y,
		int c_x, int c_y,
		RGBA color);
}