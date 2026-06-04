#include <pybind11/pybind11.h>
#include <libxslt/xslt.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <libxml/parser.h>
#include <libxml/xmlversion.h>
#include <string>
#include <stdexcept>

namespace py = pybind11;

std::string transform(const std::string& xml_src, const std::string& xsl_src) {
    xmlInitParser();

    xmlDocPtr xml_doc = xmlParseMemory(xml_src.c_str(), static_cast<int>(xml_src.size()));
    if (!xml_doc) throw std::runtime_error("Failed to parse XML");

    xmlDocPtr xsl_doc = xmlParseMemory(xsl_src.c_str(), static_cast<int>(xsl_src.size()));
    if (!xsl_doc) { xmlFreeDoc(xml_doc); throw std::runtime_error("Failed to parse XSL"); }

    xsltStylesheetPtr sheet = xsltParseStylesheetDoc(xsl_doc);
    if (!sheet) { xmlFreeDoc(xml_doc); throw std::runtime_error("Failed to compile stylesheet"); }

    xmlDocPtr result = xsltApplyStylesheet(sheet, xml_doc, nullptr);
    if (!result) { xsltFreeStylesheet(sheet); xmlFreeDoc(xml_doc); throw std::runtime_error("Transform failed"); }

    xmlChar* output = nullptr;
    int length = 0;
    xsltSaveResultToString(&output, &length, result, sheet);

    std::string out(reinterpret_cast<char*>(output), length);
    xmlFree(output);
    xmlFreeDoc(result);
    xsltFreeStylesheet(sheet);
    xmlFreeDoc(xml_doc);
    return out;
}

std::string libxml2_version() { return LIBXML_DOTTED_VERSION; }
std::string libxslt_version() { return LIBXSLT_DOTTED_VERSION; }

PYBIND11_MODULE(_core, m) {
    m.doc() = "pybind11 extension using libxslt (shared) and libxml2 (shared, transitive). "
              "zlib is a transitive dep of libxml2 and is linked statically.";
    m.def("transform", &transform, py::arg("xml"), py::arg("xsl"),
          "Apply an XSL stylesheet to an XML string and return the result.");
    m.def("libxml2_version", &libxml2_version, "Return the libxml2 version used at build time.");
    m.def("libxslt_version", &libxslt_version, "Return the libxslt version used at build time.");
}
