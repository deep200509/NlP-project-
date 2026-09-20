"""Generates main.py: the FastAPI application with one route per endpoint in the specification."""
from app.code_generator.model_generator import TYPE_MAP


def _list_route(spec: dict, endpoint: dict) -> list:
    model, plural = spec["model_name"], spec["resource_plural"]
    params = endpoint.get("query_params", [])
    signature, call = [], ["db", "skip=skip", "limit=limit"]
    signature.append("    skip: int = Query(0, ge=0, description=\"How many rows to skip\"),")
    signature.append("    limit: int = Query(100, ge=1, le=500, description=\"Maximum rows to return\"),")
    for p in params:
        if p["kind"] in ("min", "max", "equals"):
            python_type = TYPE_MAP[p["type"]][1]
            words = {"min": "Minimum", "max": "Maximum", "equals": "Exact"}[p["kind"]]
            # the variable gets a safe name; "alias" keeps the public name from the specification
            signature.append(f"    f_{p['name']}: {python_type} | None = Query(None, alias=\"{p['name']}\", "
                             f"description=\"{words} {p['field']}\"),")
            call.append(f"f_{p['name']}=f_{p['name']}")
        elif p["kind"] == "sort_by":
            allowed = ", ".join(f'"{a}"' for a in p["allowed"])
            signature.append(f"    sort_by: Literal[{allowed}] = \"id\",")
            call.append("sort_by=sort_by")
        elif p["kind"] == "order":
            signature.append("    order: Literal[\"asc\", \"desc\"] = \"asc\",")
            call.append("order=order")
    return [
        f'@app.get("{endpoint["path"]}", response_model=list[schemas.{model}Out], summary="{endpoint["summary"]}")',
        f"def list_{plural}(",
        *signature,
        "    db: Session = Depends(get_db),",
        "):",
        f"    return crud.get_{plural}({', '.join(call)})",
    ]


def generate_main(spec: dict) -> str:
    model, resource, plural = spec["model_name"], spec["resource"], spec["resource_plural"]
    id_name = f"{resource}_id"
    not_found = [
        f"    item = crud.get_{resource}(db, {id_name})",
        "    if item is None:",
        f'        raise HTTPException(status_code=404, detail="{model} not found")',
    ]
    conflict = [
        "    except IntegrityError:",
        "        db.rollback()",
        '        raise HTTPException(status_code=409, detail="Database rule broken: duplicate unique value or missing required value")',
    ]
    lines = [
        f'"""{spec["project_name"]}. Generated automatically from the API specification."""',
        "from typing import Literal",
        "",
        "from fastapi import Depends, FastAPI, HTTPException, Query, Response",
        "from sqlalchemy.exc import IntegrityError",
        "from sqlalchemy.orm import Session",
        "",
        "import crud",
        "import schemas",
        "from database import Base, engine, get_db",
        "",
        "Base.metadata.create_all(bind=engine)  # creates the table if it does not exist",
        "",
        f'app = FastAPI(title="{spec["project_name"]}", version="1.0.0",',
        f'              description="REST API for {plural}, generated from a natural-language requirement.")',
        "",
        "",
        '@app.get("/", summary="API information")',
        "def root():",
        f'    return {{"name": "{spec["project_name"]}", "docs": "/docs"}}',
    ]

    for endpoint in spec["endpoints"]:
        path = endpoint["path"].replace("{id}", "{" + id_name + "}")
        summary = endpoint["summary"]
        lines += ["", ""]
        operation = endpoint["operation"]
        if operation == "create":
            lines += [
                f'@app.post("{path}", response_model=schemas.{model}Out, status_code=201, summary="{summary}")',
                f"def create_{resource}(payload: schemas.{model}Create, db: Session = Depends(get_db)):",
                "    try:",
                f"        return crud.create_{resource}(db, payload)",
                *conflict,
            ]
        elif operation == "read_all":
            lines += _list_route(spec, endpoint)
        elif operation == "search":
            lines += [
                f'@app.get("{path}", response_model=list[schemas.{model}Out], summary="{summary}")',
                f'def search_{plural}(q: str = Query(..., min_length=1, description="Keyword to look for"),',
                f"{' ' * (len('def search_') + len(plural) + 1)}db: Session = Depends(get_db)):",
                f"    return crud.search_{plural}(db, q)",
            ]
        elif operation == "read_one":
            lines += [
                f'@app.get("{path}", response_model=schemas.{model}Out, summary="{summary}")',
                f"def read_{resource}({id_name}: int, db: Session = Depends(get_db)):",
                *not_found,
                "    return item",
            ]
        elif operation == "update":
            lines += [
                f'@app.put("{path}", response_model=schemas.{model}Out, summary="{summary}")',
                f"def update_{resource}({id_name}: int, payload: schemas.{model}Update, db: Session = Depends(get_db)):",
                *not_found,
                "    try:",
                f"        return crud.update_{resource}(db, item, payload)",
                *conflict,
            ]
        elif operation == "delete":
            lines += [
                f'@app.delete("{path}", status_code=204, summary="{summary}")',
                f"def delete_{resource}({id_name}: int, db: Session = Depends(get_db)):",
                *not_found,
                f"    crud.delete_{resource}(db, item)",
                "    return Response(status_code=204)",
            ]
    return "\n".join(lines) + "\n"