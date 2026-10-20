"""Read an AR XML file into the JSON shape AR uses for its XML-shaped _json.txt files.

An element with children becomes an object keyed by child name; a name that
repeats becomes a list, and a single child stays an object, as in _json.txt.
A leaf becomes its text, and an empty element becomes null. Namespace
declarations are dropped; other attributes become "@name" keys.
"""

from xml.etree import ElementTree


class XmlError(ValueError):
    pass


def _name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _value(el):
    attrs = {f"@{_name(k)}": v for k, v in el.attrib.items() if not k.startswith("{")}
    children = list(el)
    text = (el.text or "").strip()
    if not children and not attrs:
        return text or None
    out = dict(attrs)
    for child in children:
        key, value = _name(child.tag), _value(child)
        if key not in out:
            out[key] = value
        elif isinstance(out[key], list):
            out[key].append(value)
        else:
            out[key] = [out[key], value]
    if text:
        out["#text"] = text
    return out


def xml_to_data(body: bytes):
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as e:
        raise XmlError(str(e)) from None
    return {_name(root.tag): _value(root)}
