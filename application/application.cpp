#include "application.h"
#include "engine.h"

#include <iostream>
#include <cmath>

#include "ImageRGBA.h"



void draw_rectangle(ImageRGBA& image, int x_min, int y_min, int x_max, int y_max, RGBA color)
{
	for(int y = y_min; y <= y_max; y++)
	{
		for(int x = x_min; x <= x_max; x++)
		{
			ImageRGBA_::set_pixel(image, x, y, color);
		}
	}
}


void draw_line(ImageRGBA& image, int a_x, int a_y, int b_x, int b_y, RGBA color)
{
	int dx = a_x - b_x;
	int dy = a_y - b_y;

	int steps = std::max(abs(dx), abs(dy));

	// int width = ImageRGBA_::get_width();
	// int height = ImageRGBA_::get_height();


	// A line whose start and end are the same point.
	if (steps == 0)
	{
		ImageRGBA_::set_pixel(image, a_x, a_y, color);
		return;
	}

	float x = float(a_x);
	float y = float(a_y);

	float step_x = float(dx) / float(steps);
	float step_y = float(dy) / float(steps);


	for (int i = 0; i < steps; ++i)
	{
		std::cout << "i : " << i << "\n";

		ImageRGBA_::set_pixel
		(
			image,
			int(std::round(x)),
			int(std::round(y)),
			color
		);

		x += step_x;
		y += step_y;
	}

	
}

int run_application()
{
    const int value = engine_calculate_example_value();

    std::cout << "Application result: " << value << '\n';

	auto image = ImageRGBA_::create(1024, 1024);
	if (!image)
	{
		std::cerr << "Failed to create image.\n";
		return 1;
	}
	
	
	ImageRGBA_::for_every_pixel_UV
	(
		*image,
		[](RGBA color_input, float u, float v)
		{
			RGBA color;
			
			color.r = 0;
			color.g = static_cast<uint8_t>(u * 255.0f);
			color.b = static_cast<uint8_t>(v * 255.0f);
			color.a = 255;
			
			return color;
		}
	);
	
	
	for(int i = 0; i < 100; i++)
	{
		RGBA color;
		color.r = 100;
		color.b = 120;
		color.b = 220;
		color.a = 255;
		
		ImageRGBA_::set_pixel(*image, i, i, color);
	}
	
	draw_rectangle(*image, 10, 110, 200, 400, RGBA(100, 200, 255, 255));
	
	{
		RGBA color;
		color.r = 100;
		color.b = 120;
		color.b = 220;
		color.a = 255;

		draw_line(*image, 100, 100, 220, 1000, color);
	}

	
	ImageRGBA_::save_png(*image, "output.png");

    ImageRGBA_::free_image(image);
	
	
	std::cout << "----------------------- \n";
	std::cout << "Writing the image \n";
	std::cout << "----------------------- \n";
	
    return value == 42 ? 0 : 1;
}
