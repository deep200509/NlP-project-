"""Generates models.py: the SQLAlchemy model = the database table (database generation)."""

# spec type -> (SQLAlchemy column type, Python type used in annotations)
TYPE_MAP = {
    "string": ("String(255)", "str"),
    "email": ("String(255)", "str"),
    "text": ("Text", "str"),
    "integer": ("Integer", "int"),
    "float": ("Float", "float"),
    "boolean": ("Boolean", "bool"),
    "date": ("Date", "dt.date"),
    "datetime": ("DateTime", "dt.datetime"),
}


def generate_models(spec: dict) -> str:
    lines = [
        '"""Database model. Generated automatically from the API specification."""',
        "import datetime as dt",
        "",
        "from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text",
        "from sqlalchemy.orm import Mapped, mapped_column",
        "",
        "from database import Base",
        "",
        "",
        f"class {spec['model_name']}(Base):",
        f'    __tablename__ = "{spec["table_name"]}"',
        "",
        "    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)",
    ]
    for field in spec["fields"]:
        column_type, python_type = TYPE_MAP[field["type"]]
        required = field.get("required", True)
        annotation = python_type if required else f"{python_type} | None"
        options = [column_type, f"nullable={not required}"]
        if field.get("unique"):
            options.append("unique=True")
        lines.append(f"    {field['name']}: Mapped[{annotation}] = mapped_column({', '.join(options)})")
    return "\n".join(lines) + "\n"