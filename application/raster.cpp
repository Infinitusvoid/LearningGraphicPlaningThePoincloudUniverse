#include "raster.h"

#include <iostream>
#include <cmath>
#include <cassert>

namespace Raster_
{
	void draw_rectangle(ImageRGBA& image, int x_min, int y_min, int x_max, int y_max, RGBA color)
	{
		for (int y = y_min; y <= y_max; y++)
		{
			for (int x = x_min; x <= x_max; x++)
			{
				ImageRGBA_::set_pixel(image, x, y, color);
			}
		}
	}
	
	bool clip_line_to_image(
		const ImageRGBA& image,
		float& a_x,
		float& a_y,
		float& b_x,
		float& b_y)
	{
		float image_min_x = 0.0f;
		float image_min_y = 0.0f;

		float image_max_x = float(ImageRGBA_::get_width(image) - 1);
		float image_max_y = float(ImageRGBA_::get_height(image) - 1);

		float dx = b_x - a_x;
		float dy = b_y - a_y;

		// We begin by assuming that the whole line is visible.
		//
		// P(t) = A + (B - A) * t
		//
		// t = 0 -> A
		// t = 1 -> B

		float visible_t_start = 0.0f;
		float visible_t_end = 1.0f;


		auto restrict_visible_range_to_axis =
			[&](
				float line_start,
				float line_movement,
				float axis_min,
				float axis_max)
			{
				// The line does not move along this axis.
				if (line_movement == 0.0f)
				{
					// If it is outside the allowed range,
					// the entire line is outside the image.
					return
						line_start >= axis_min &&
						line_start <= axis_max;
				}


				// At what t does the line cross each side
				// of the allowed range?

				float t_at_min =
					(axis_min - line_start) / line_movement;

				float t_at_max =
					(axis_max - line_start) / line_movement;


				// Depending on the direction of the line,
				// these may be reversed.

				if (t_at_min > t_at_max)
					std::swap(t_at_min, t_at_max);


				// Restrict the currently visible part of the line.

				visible_t_start =
					std::max(visible_t_start, t_at_min);

				visible_t_end =
					std::min(visible_t_end, t_at_max);


				// If the range collapsed, nothing is visible.

				return visible_t_start <= visible_t_end;
			};


		// First ask:
		//
		// "For what part of the line is X inside the image?"

		if (!restrict_visible_range_to_axis(
			a_x,
			dx,
			image_min_x,
			image_max_x))
		{
			return false;
		}


		// Then ask:
		//
		// "For what part of the line is Y inside the image?"

		if (!restrict_visible_range_to_axis(
			a_y,
			dy,
			image_min_y,
			image_max_y))
		{
			return false;
		}


		float original_a_x = a_x;
		float original_a_y = a_y;


		// Move A to where the visible part begins.

		a_x = original_a_x + dx * visible_t_start;
		a_y = original_a_y + dy * visible_t_start;


		// Move B to where the visible part ends.

		b_x = original_a_x + dx * visible_t_end;
		b_y = original_a_y + dy * visible_t_end;


		return true;
	}

	void draw_line(
		ImageRGBA& image,
		int a_x,
		int a_y,
		int b_x,
		int b_y,
		RGBA color)
	{
		// Convert the original line to floating point because clipping
		// may move either endpoint to a position between integer pixels.

		float clipped_a_x = float(a_x);
		float clipped_a_y = float(a_y);

		float clipped_b_x = float(b_x);
		float clipped_b_y = float(b_y);


		// Find the part of the line that is actually inside the image.

		if (!clip_line_to_image(
			image,
			clipped_a_x,
			clipped_a_y,
			clipped_b_x,
			clipped_b_y))
		{
			return;
		}


		float dx = clipped_b_x - clipped_a_x;
		float dy = clipped_b_y - clipped_a_y;


		// Walk through continuous space in increments small enough
		// that we never skip a pixel row or column.

		int steps = int(std::ceil(
			std::max(std::abs(dx), std::abs(dy))
		));


		// The visible line collapsed to one point.

		if (steps == 0)
		{
			ImageRGBA_::set_pixel(
				image,
				int(std::round(clipped_a_x)),
				int(std::round(clipped_a_y)),
				color);

			return;
		}


		float x = clipped_a_x;
		float y = clipped_a_y;

		float step_x = dx / float(steps);
		float step_y = dy / float(steps);


		for (int i = 0; i < steps; i++)
		{
			ImageRGBA_::set_pixel(
				image,
				int(std::round(x)),
				int(std::round(y)),
				color);

			x += step_x;
			y += step_y;
		}


		// Explicitly draw the final visible endpoint.

		ImageRGBA_::set_pixel(
			image,
			int(std::round(clipped_b_x)),
			int(std::round(clipped_b_y)),
			color);
	}

	void draw_triangle_wireframe(
		ImageRGBA& image,
		int a_x, int a_y,
		int b_x, int b_y,
		int c_x, int c_y,
		RGBA color)
	{
		draw_line(image, a_x, a_y, b_x, b_y, color);
		draw_line(image, b_x, b_y, c_x, c_y, color);
		draw_line(image, c_x, c_y, a_x, a_y, color);
	}
}

