#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <fmt/core.h>
#include <fmt/color.h>
#include <string>

static PyObject* myadder_add(PyObject* self, PyObject* args) {
    double a, b;
    
    if (!PyArg_ParseTuple(args, "dd", &a, &b)) {
        return NULL;
    }
    
    double result = a + b;
    fmt::print(fg(fmt::color::green) | fmt::emphasis::bold,
               "myadder: {} + {} = {}\n", a, b, result);
    
    return PyFloat_FromDouble(result);
}

static PyObject* myadder_add_integers(PyObject* self, PyObject* args) {
    long a, b;
    
    if (!PyArg_ParseTuple(args, "ll", &a, &b)) {
        return NULL;
    }
    
    long result = a + b;
    fmt::print(fg(fmt::color::cyan) | fmt::emphasis::bold,
               "myadder (integers): {} + {} = {}\n", a, b, result);
    
    return PyLong_FromLong(result);
}

static PyObject* myadder_greet(PyObject* self, PyObject* args) {
    const char* name;
    
    if (!PyArg_ParseTuple(args, "s", &name)) {
        return NULL;
    }
    
    std::string greeting = fmt::format("Hello, {}! Formatted by fmt.", name);
    fmt::print(fg(fmt::color::yellow) | fmt::emphasis::italic,
               "{}\n", greeting);
    
    return PyUnicode_FromString(greeting.c_str());
}

static PyMethodDef MyadderMethods[] = {
    {
        "add",
        myadder_add,
        METH_VARARGS,
        "Add two numbers. Prints colored output to terminal."
    },
    {
        "add_integers",
        myadder_add_integers,
        METH_VARARGS,
        "Add two integers. Prints colored output to terminal."
    },
    {
        "greet",
        myadder_greet,
        METH_VARARGS,
        "Return a greeting formatted with fmt. Takes a name as argument."
    },
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef myaddermodule = {
    PyModuleDef_HEAD_INIT,
    "myadder._core",
    "Example Python extension using fmt library via Conan.",
    -1,
    MyadderMethods
};

PyMODINIT_FUNC PyInit__core(void) {
    return PyModule_Create(&myaddermodule);
}
