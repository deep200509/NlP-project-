"""Generates schemas.py: Pydantic models that validate every request and shape every response."""
from app.code_generator.model_generator import TYPE_MAP


def _field_line(field: dict, force_optional: bool) -> str:
    python_type = TYPE_MAP[field["type"]][1]
    optional = force_optional or not field.get("required", True)
    rules = []
    if field["type"] in ("string", "email"):
        rules += ["min_length=1", "max_length=255"]
    if field["type"] == "email":
        rules.append("pattern=EMAIL_PATTERN")

    annotation = f"{python_type} | None" if optional else python_type
    if optional:
        rules.insert(0, "default=None")
    if rules:
        return f"    {field['name']}: {annotation} = Field({', '.join(rules)})"
    return f"    {field['name']}: {annotation}"


def generate_schemas(spec: dict) -> str:
    model = spec["model_name"]
    lines = [
        '"""Request and response schemas. Generated automatically from the API specification."""',
        "import datetime as dt",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        'EMAIL_PATTERN = r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"',
        "",
        "",
        f"class {model}Base(BaseModel):",
    ]
    lines += [_field_line(f, force_optional=False) for f in spec["fields"]]
    lines += [
        "",
        "",
        f"class {model}Create({model}Base):",
        f'    """Body of POST requests."""',
        "",
        "",
        f"class {model}Update(BaseModel):",
        f'    """Body of PUT requests: send only the fields you want to change."""',
    ]
    lines += [_field_line(f, force_optional=True) for f in spec["fields"]]
    lines += [
        "",
        "",
        f"class {model}Out({model}Base):",
        f'    """What the API sends back."""',
        "    model_config = ConfigDict(from_attributes=True)",
        "",
        "    id: int",
    ]
    return "\n".join(lines) + "\n"