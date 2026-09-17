#pragma once

#include <cstdio>
#include <filesystem>
#include <iostream>
#include <string>

// Only things that *every* sketch may need go here.
// Nothing sketch-specific: no triangles, no edge visualizations,
// no colors tied to one experiment.
//
// Each sketch file stays self-contained and is free to duplicate
// its own setup (points, loops, wireframe colors, ...).
//
// Convention: every sketch has a number (0, 1, ..., 11, ...).
// The structured prefix "run_sketch_<NNNN>" is built in exactly
// one place below, and every output file lives under
// "output/<prefix>/" so sketches never pollute the source root
// and never clash with each other.

namespace SketchCommon
{
	inline void print_header(const char* sketch_name)
	{
		std::cout << "\n";
		std::cout << "----------------------- \n";
		std::cout << sketch_name << "\n";
		std::cout << "----------------------- \n";
	}

	// "run_sketch_0010" for 10. Single place that owns the structure.
	inline std::string sketch_prefix_for_number(int sketch_number)
	{
		char buf[64];
		std::snprintf(buf, sizeof(buf), "run_sketch_%04d", sketch_number);
		return std::string(buf);
	}

	// Full structured name from two numbers:
	//   run_sketch_<sketch_number>_<artifact_number>_<slug>
	// e.g. output_path(7, 2, "BC_visualization.png") ->
	//   "output/run_sketch_0007/run_sketch_0007_2_BC_visualization.png"
	// The folder is created. Sketches never format names themselves.
	inline std::string output_path(int sketch_number, int artifact_number, const std::string& slug)
	{
		std::string prefix = sketch_prefix_for_number(sketch_number);

		char basename[256];
		std::snprintf(basename, sizeof(basename), "%s_%d_%s",
			prefix.c_str(), artifact_number, slug.c_str());

		std::filesystem::path dir = std::filesystem::path("output") / prefix;

		std::error_code ec;
		std::filesystem::create_directories(dir, ec);
		if (ec)
		{
			std::cerr << "[SketchCommon] could not create " << dir << ": " << ec.message() << "\n";
		}

		return (dir / basename).string();
	}
}
