"""Word lists (linguistic knowledge) used by the rule-based parts of the NLP pipeline."""

# Seed verbs for every intent. Used (1) to spot which chunks of a sentence
# describe an operation and (2) as anchors for semantic similarity.
INTENT_SEEDS = {
    "CREATE": ["add", "create", "insert", "register", "enroll", "save", "store", "submit", "post", "enter"],
    "READ": ["get", "view", "show", "list", "display", "fetch", "retrieve", "see", "read", "return"],
    "UPDATE": ["update", "edit", "modify", "change", "correct", "revise", "alter", "replace", "amend"],
    "DELETE": ["delete", "remove", "erase", "drop", "discard", "eliminate", "destroy", "wipe"],
    "SEARCH": ["search", "find", "lookup", "look", "query", "locate"],
    "FILTER": ["filter", "narrow"],
    "SORT": ["sort", "order", "arrange", "rank"],
    "AUTHENTICATION": ["login", "log", "sign", "signup", "authenticate", "authorize", "secure", "protect", "restrict"],
}
ACTION_LEXICON = {verb: intent for intent, verbs in INTENT_SEEDS.items() for verb in verbs}

# Order used when listing operations in the final result
CANONICAL_ORDER = ["create", "read", "update", "delete", "search", "filter", "sort", "authentication"]

# Nouns that are never the resource of an API
GENERIC_NOUNS = {
    "api", "system", "application", "app", "backend", "service", "platform", "project",
    "website", "software", "management", "database", "data", "detail", "information",
    "info", "record", "list", "operation", "field", "attribute", "property", "endpoint",
    "id", "crud", "ability", "feature", "functionality", "option", "thing", "way",
    "keyword", "value", "range", "result", "entry", "item", "one", "all",
    "rest", "restful", "web", "json", "http", "server", "table", "model", "name",
    "datum", "managing", "user_id",
}
# People who USE the api. Only chosen as the resource when nothing else is found.
ACTOR_WORDS = {"user", "admin", "administrator", "people", "person", "staff", "anyone", "everyone"}

# ---- data type knowledge -------------------------------------------------
TYPE_LEXICON = {
    "email": "email", "mail": "email",
    "age": "integer", "quantity": "integer", "qty": "integer", "count": "integer",
    "stock": "integer", "year": "integer", "semester": "integer", "pages": "integer",
    "page": "integer", "floor": "integer", "capacity": "integer", "duration": "integer",
    "experience": "integer", "seats": "integer", "seat": "integer", "marks": "integer",
    "price": "float", "salary": "float", "amount": "float", "cost": "float", "fee": "float",
    "fees": "float", "rating": "float", "gpa": "float", "cgpa": "float", "percentage": "float",
    "weight": "float", "height": "float", "balance": "float", "total": "float",
    "discount": "float", "latitude": "float", "longitude": "float", "score": "float",
    "date": "date", "dob": "date", "birthday": "date", "birthdate": "date", "deadline": "date",
    "time": "datetime", "timestamp": "datetime",
    "availability": "boolean", "available": "boolean", "active": "boolean",
    "verified": "boolean", "completed": "boolean", "paid": "boolean", "enabled": "boolean",
    "description": "text", "bio": "text", "notes": "text", "note": "text", "summary": "text",
    "content": "text", "comment": "text", "review": "text", "message": "text",
    "name": "string", "title": "string", "phone": "string", "mobile": "string",
    "address": "string", "city": "string", "country": "string", "state": "string",
    "course": "string", "department": "string", "category": "string", "status": "string",
    "author": "string", "isbn": "string", "gender": "string", "password": "string",
    "username": "string", "role": "string", "type": "string", "code": "string",
    "number": "string", "brand": "string", "model": "string", "color": "string",
    "genre": "string", "language": "string", "publisher": "string", "designation": "string",
}
# Anchor words per type, for fields that are in no list ("wage" is close to "salary" -> float)
TYPE_PROTOTYPES = {
    "integer": ["age", "quantity", "count", "year"],
    "float": ["price", "salary", "cost", "amount", "rating"],
    "date": ["date", "birthday", "deadline"],
    "boolean": ["available", "active", "enabled"],
    "text": ["description", "comment", "summary"],
}