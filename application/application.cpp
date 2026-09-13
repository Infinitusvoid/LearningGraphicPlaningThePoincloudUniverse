#include "application.h"
#include "engine.h"

#include <iostream>

#include "ImageRGBA.h"

int run_application()
{
    const int value = engine_calculate_example_value();

    std::cout << "Application result: " << value << '\n';

    return value == 42 ? 0 : 1;
}
