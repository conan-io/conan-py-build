#pragma once
#include <fmt/format.h>
#include <string>

inline std::string format_result(double value, int n) {
    return fmt::format("sum_of_squares({} values) = {:.4f}", n, value);
}
