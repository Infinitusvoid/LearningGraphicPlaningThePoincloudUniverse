#include "application.h"
#include "engine.h"

#include <iostream>
#include <cmath>
#include <cassert>

#include "raster.h"

namespace Sketch
{
	using namespace Math_;
	using namespace Raster_;

	int run_sketch_0000()
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


		for (int i = 0; i < 100; i++)
		{
			RGBA color;
			color.r = 100;
			color.g = 120;
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

		{
			draw_triangle_wireframe(
				*image,
				100, 100,
				800, 250,
				350, 850,
				RGBA(255, 255, 255, 255));
		}


		ImageRGBA_::save_png(*image, "output.png");

		ImageRGBA_::free_image(image);


		std::cout << "----------------------- \n";
		std::cout << "Writing the image \n";
		std::cout << "----------------------- \n";

		return value == 42 ? 0 : 1;
	}

	int run_sketch_0001_visualization_edge_function_edge_AB()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0001_visualization_edge_function_edge_AB\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a( (image_size / 10) * 1, (image_size / 10) * 9);
		Point b( (image_size / 10) * 4, (image_size / 10) * 2);
		Point c( (image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// AB
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(a.x), float(a.y), float(b.x), float(b.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0001_0_visualization_edge_function_edge_AB.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0002_visualization_edge_function_edge_BC()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0002_visualization_edge_function_edge_BC\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// BC
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(b.x), float(b.y), float(c.x), float(c.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0002_0_visualization_edge_function_edge_BC.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0003_visualization_edge_function_edge_CA()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0003_visualization_edge_function_edge_CA\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// BC
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(c.x), float(c.y), float(a.x), float(a.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0003_0_visualization_edge_function_edge_CA.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0004_visualization_edge_function_edge_AC()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0004_0_visualization_edge_function_edge_AC\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// BC
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(a.x), float(a.y), float(c.x), float(c.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0004_0_visualization_edge_function_edge_AC.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0005_visualization_edge_function_edge_CB()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0005_0_visualization_edge_function_edge_CB\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// BC
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(c.x), float(c.y), float(b.x), float(b.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0005_0_visualization_edge_function_edge_CB.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0006_visualization_edge_function_edge_BA()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0006_0_visualization_edge_function_edge_BA\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		// AB
		{
			int width = ImageRGBA_::get_width(*image);
			int height = ImageRGBA_::get_height(*image);

			for (int y = 0; y < height; y++)
			{
				for (int x = 0; x < width; x++)
				{
					float value = Math_::edge_function(float(b.x), float(b.y), float(a.x), float(a.y), float(x), float(y));

					if (value > 0)
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 100, 100, 255));
					}
					else
					{
						ImageRGBA_::set_pixel(*image, x, y, RGBA(0, 0, 0, 255));
					}
				}
			}
		}

		Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);

		ImageRGBA_::save_png(*image, "run_sketch_0006_0_visualization_edge_function_edge_BA.png");

		ImageRGBA_::free_image(image);

		return 0;
	}

	int run_sketch_0007_visualization_edge_function_edge_Magnitude_with_sin_functions()
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";

		std::cout << "run_sketch_0007_visualization_edge_function_edge_Magnitude_with_sin_functions\n";
		std::cout << "----------------------- \n";
		// we define the triangle

		struct Point
		{
			int x;
			int y;
		};

		const int image_size = 1024;

		Point a((image_size / 10) * 1, (image_size / 10) * 9);
		Point b((image_size / 10) * 4, (image_size / 10) * 2);
		Point c((image_size / 10) * 9, (image_size / 10) * 9);

		ImageRGBA* image = ImageRGBA_::create(image_size, image_size);

		RGBA color;
		color.r = 0;
		color.g = 200;
		color.b = 200;
		color.a = 255;

		auto draw_edge_from_to = [&](ImageRGBA& img, Point start, Point end)
			{
				int width = ImageRGBA_::get_width(img);
				int height = ImageRGBA_::get_height(img);

				for (int y = 0; y < height; y++)
				{
					for (int x = 0; x < width; x++)
					{
						float value = Math_::edge_function(float(start.x), float(start.y), float(end.x), float(end.y), float(x), float(y));

						if (value > 0)
						{
							ImageRGBA_::set_pixel(img, x, y, RGBA(0, 100, 100, 255));
						}
						else
						{
							ImageRGBA_::set_pixel(img, x, y, RGBA(0, 0, 0, 255));
						}
					}
				}
			};

		auto draw_magnitude_sin_way = [&](ImageRGBA& img, Point start, Point end)
			{
				int width = ImageRGBA_::get_width(img);
				int height = ImageRGBA_::get_height(img);

				for (int y = 0; y < height; y++)
				{
					for (int x = 0; x < width; x++)
					{
						float value = Math_::edge_function(float(start.x), float(start.y), float(end.x), float(end.y), float(x), float(y));

						RGBA color = ImageRGBA_::get_pixel(img, x, y);


						if (abs(std::sinf(value * 0.2)) < 0.2)
						{
							color.b = 255;
						}




						ImageRGBA_::set_pixel(img, x, y, RGBA(color.r, color.g, color.b, 255));

					}
				}
			};


		{
			Point w_a = a;
			Point w_b = b;

			Point w_c = c;

			// AB
			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_a, w_b);
				draw_magnitude_sin_way(*image, w_a, w_b);
				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_0_AB_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}

			// BA
			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_b, w_a);
				draw_magnitude_sin_way(*image, w_b, w_a);

				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_1_BA_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}
		}

		{
			Point w_a = b;
			Point w_b = c;

			Point w_c = a;

			
			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_a, w_b);
				draw_magnitude_sin_way(*image, w_a, w_b);
				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_2_AB_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}

			
			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_b, w_a);
				draw_magnitude_sin_way(*image, w_b, w_a);

				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_3_BA_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}
		}

		{
			Point w_a = c;
			Point w_b = a;

			Point w_c = b;


			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_a, w_b);
				draw_magnitude_sin_way(*image, w_a, w_b);
				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_4_AB_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}


			{
				ImageRGBA_::clear_with_color(*image, RGBA(0, 0, 0, 255));
				draw_edge_from_to(*image, w_b, w_a);
				draw_magnitude_sin_way(*image, w_b, w_a);

				Raster_::draw_triangle_wireframe(*image, a.x, a.y, b.x, b.y, c.x, c.y, color);
				ImageRGBA_::save_png(*image, "run_sketch_0007_5_BA_visualization_edge_function_edge_Magnitude_with_sin_functions.png");
			}
		}

		

		

		

		

		ImageRGBA_::free_image(image);

		return 0;
	}
}









int run_application()
{
	// Sketch::run_sketch_0000();

	// Sketch::run_sketch_0002_visualization_edge_function_edge_BC();
	// Sketch::run_sketch_0003_visualization_edge_function_edge_CA();

	// Sketch::run_sketch_0004_visualization_edge_function_edge_AC();
	// Sketch::run_sketch_0005_visualization_edge_function_edge_CB();
	// Sketch::run_sketch_0006_visualization_edge_function_edge_BA();

	Sketch::run_sketch_0007_visualization_edge_function_edge_Magnitude_with_sin_functions();
	
	// The magnitude of the edge function 
	// use as well sin(value) trick to show the change 

	// Than there is realization that this edge function splits 2d plane on two half 
	// There is for sure equivalent in 3d that for plane splits the 3d space and than generalization into any dimension basically 

	// The realization when you will be able to render many 3d frames you will be able to train gaussian splat
	// Well yea and you will know how to render spherical panorama and as well cubemap as well

	// The book Mathemattics for computer graphic may go well along 
	// Find any sources but play and make nice images 

	return 0;
}


