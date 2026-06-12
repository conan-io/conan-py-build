# distutils: language = c++
from libcpp.string cimport string

cdef extern from "formatter.h":
    string format_result(double value, int n)


def sum_of_squares(list values) -> str:
    """Compute sum of squares with a typed Cython loop, format result with fmt."""
    cdef double total = 0.0
    cdef double x
    cdef int n = len(values)
    for x in values:
        total += x * x
    return format_result(total, n).decode("utf-8")
