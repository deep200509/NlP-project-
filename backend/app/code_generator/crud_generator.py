"""Generates crud.py: the functions that talk to the database."""


def _endpoint(spec: dict, operation: str):
    return next((e for e in spec["endpoints"] if e["operation"] == operation), None)


def generate_crud(spec: dict) -> str:
    model, resource, plural = spec["model_name"], spec["resource"], spec["resource_plural"]
    entity = f"models.{model}"
    produced = {e["operation"] for e in spec["endpoints"]}
    lines = [
        '"""Database operations. Generated automatically from the API specification."""',
        "from sqlalchemy import or_",
        "from sqlalchemy.orm import Session",
        "",
        "import models",
        "import schemas",
        "",
        "",
        f"def get_{resource}(db: Session, {resource}_id: int):",
        f"    return db.get({entity}, {resource}_id)",
    ]

    if "create" in produced:
        lines += [
            "", "",
            f"def create_{resource}(db: Session, data: schemas.{model}Create):",
            f"    item = {entity}(**data.model_dump())",
            "    db.add(item)",
            "    db.commit()",
            "    db.refresh(item)",
            "    return item",
        ]

    if "read_all" in produced:
        params = _endpoint(spec, "read_all").get("query_params", [])
        filters = [p for p in params if p["kind"] in ("min", "max", "equals")]
        has_sort = any(p["kind"] == "sort_by" for p in params)
        signature = ["db: Session", "skip: int = 0", "limit: int = 100"]
        signature += [f"f_{p['name']}=None" for p in filters]
        if has_sort:
            signature += ['sort_by: str = "id"', 'order: str = "asc"']
        lines += ["", "", f"def get_{plural}({', '.join(signature)}):", f"    query = db.query({entity})"]
        for p in filters:
            operator = {"min": ">=", "max": "<=", "equals": "=="}[p["kind"]]
            lines += [f"    if f_{p['name']} is not None:",
                      f"        query = query.filter({entity}.{p['field']} {operator} f_{p['name']})"]
        if has_sort:
            lines += [f"    column = getattr({entity}, sort_by)",
                      '    query = query.order_by(column.desc() if order == "desc" else column.asc())']
        else:
            lines.append(f"    query = query.order_by({entity}.id)")
        lines.append("    return query.offset(skip).limit(limit).all()")

    if "search" in produced:
        conditions = ", ".join(f"{entity}.{name}.ilike(pattern)" for name in _endpoint(spec, "search")["search_fields"])
        lines += [
            "", "",
            f"def search_{plural}(db: Session, q: str):",
            '    pattern = f"%{q}%"',
            f"    return db.query({entity}).filter(or_({conditions})).order_by({entity}.id).all()",
        ]

    if "update" in produced:
        lines += [
            "", "",
            f"def update_{resource}(db: Session, item: {entity}, data: schemas.{model}Update):",
            "    for key, value in data.model_dump(exclude_unset=True).items():",
            "        setattr(item, key, value)",
            "    db.commit()",
            "    db.refresh(item)",
            "    return item",
        ]

    if "delete" in produced:
        lines += [
            "", "",
            f"def delete_{resource}(db: Session, item: {entity}) -> None:",
            "    db.delete(item)",
            "    db.commit()",
        ]
    return "\n".join(lines) + "\n"