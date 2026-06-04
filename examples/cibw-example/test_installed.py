import myxslt_cibw

xml = "<root><n>Conan</n></root>"
xsl = (
    '<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">'
    '<xsl:template match="/"><out><xsl:value-of select="root/n"/></out></xsl:template>'
    "</xsl:stylesheet>"
)
out = myxslt_cibw.transform(xml, xsl)
assert "Conan" in out, f"unexpected: {out!r}"
print("transform ok:", out.strip())
