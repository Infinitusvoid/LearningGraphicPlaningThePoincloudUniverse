#include "application.h"
#include "engine.h"

#include <iostream>

#include "ImageRGBA.h"

int run_application()
{
    const int value = engine_calculate_example_value();

    std::cout << "Application result: " << value << '\n';

	auto image = ImageRGBA_::create(1024, 1024);
	
	/*
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
	*/
	// ImageRGBA_::save_png(image, "output.png");

    return value == 42 ? 0 : 1;
}
