#include "tests.h"

#include "engine.h"
#include "my_lib.h"

#include <iostream>

bool run_all_tests()
{
    if (add_numbers(2, 3) != 5)
    {
        std::cerr << "TEST FAILED: add_numbers\n";
        return false;
    }

    if (engine_calculate_example_value() != 42)
    {
        std::cerr << "TEST FAILED: engine_calculate_example_value\n";
        return false;
    }

    std::cout << "ALL TESTS PASSED\n";
    return true;
}

int main()
{
    return run_all_tests() ? 0 : 1;
}
