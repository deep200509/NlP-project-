"""
Builds datasets/intent_dataset.csv for the intent classifier.

Each PATTERN is a hand-written way of phrasing a requirement.
{e}  = entity, singular (student)     {es} = entity, plural (students)
{f}, {f2} = field names (price, email) {n}, {n2} = numbers

Every pattern is filled with a few random entities, so ~190 patterns
become ~700 training sentences. To grow the dataset, just add patterns
or entities and run this script again.
"""
import csv
import random
from pathlib import Path

random.seed(42)  # same "random" choices every run, so results are repeatable

ENTITIES = {
    "student": "students", "book": "books", "employee": "employees",
    "product": "products", "customer": "customers", "order": "orders",
    "teacher": "teachers", "course": "courses", "patient": "patients",
    "doctor": "doctors", "invoice": "invoices", "ticket": "tickets",
    "vehicle": "vehicles", "movie": "movies", "hotel": "hotels",
    "supplier": "suppliers",
}
FIELDS = ["name", "title", "email", "price", "age", "date", "status",
          "city", "category", "salary", "rating", "phone"]

PATTERNS = {
    "CREATE": [
        "add a new {e}",
        "create a {e}",
        "enroll a new {e} in the system",
        "insert a {e} record",
        "users should be able to add {es}",
        "allow admin to create new {es}",
        "i want to add a {e} with {f} and {f2}",
        "make a new {e} entry",
        "save a new {e} to the database",
        "store {e} details",
        "submit a new {e}",
        "post a new {e}",
        "the system should let users create {es}",
        "new {e} creation",
        "add {e} information to the system",
        "enter a new {e} record",
        "build an endpoint to add {es}",
        "create {e} with {f}",
        "insert new {es} into the database",
        "users can enroll {es}",
        "save {e} details such as {f} and {f2}",
        "store a new {e} in the system",
        "users can submit {es}",
        "endpoint to post {es}",
        "make {es} and keep them in the database",
        "enter {e} details like {f}",
    ],
    "READ": [
        "show all {es}",
        "get {e} details",
        "view all {es}",
        "list all {es}",
        "display the list of {es}",
        "fetch a {e} by id",
        "get a single {e} using its id",
        "retrieve all {e} records",
        "users can view {es}",
        "see every {e} in the system",
        "read {e} information",
        "return all {es}",
        "view {e} profile",
        "get the details of one {e}",
        "show me the {es}",
        "fetch all the {es} from the database",
        "find a {e} by id",
        "list every {e}",
        "display {e} details by id",
        "retrieve a {e} using its id",
        "users can see all {es}",
        "read all {e} records",
        "return the {e} with a given id",
        "get every {e}",
        "find a {e} using its id",
        "show the full list of {es}",
    ],
    "UPDATE": [
        "update {e} information",
        "change {e} {f}",
        "edit {e} details",
        "modify an existing {e}",
        "update the {f} of a {e}",
        "users should be able to edit {es}",
        "correct the {f} of a {e}",
        "revise {e} record",
        "alter {e} data",
        "update a {e} by id",
        "change the details of a {e}",
        "allow editing of {es}",
        "replace {e} {f} with a new value",
        "patch {e} details",
        "make changes to a {e}",
        "amend {e} information",
        "set a new {f} for the {e}",
        "users can modify {e} records",
        "correct wrong {e} details",
        "revise the {f} of a {e}",
        "alter the {f} of an existing {e}",
        "replace the old {e} details",
        "patch the {f} of a {e}",
        "amend a {e} record",
        "set {e} {f} to a different value",
        "users can update their {e} {f}",
    ],
    "DELETE": [
        "delete a {e}",
        "remove {e}",
        "erase a {e} record",
        "delete {e} by id",
        "users should be able to delete {es}",
        "remove a {e} from the system",
        "drop a {e} from the database",
        "get rid of a {e}",
        "discard {e} entry",
        "allow admin to remove {es}",
        "permanently delete {e} data",
        "clear a {e} record",
        "eliminate {e} from the list",
        "cancel and remove the {e}",
        "destroy {e} record",
        "delete all details of a {e}",
        "users can remove {es}",
        "wipe a {e} entry",
        "erase {es} from the database",
        "drop old {es}",
        "get rid of unwanted {es}",
        "discard a {e} permanently",
        "clear {es} from the system",
        "eliminate a {e} by id",
        "destroy a {e} permanently",
        "wipe {e} data from the system",
    ],
    "SEARCH": [
        "search {es} by {f}",
        "find {es} by {f}",
        "look up a {e} by {f}",
        "search for a {e} using {f}",
        "find {es} whose {f} contains a keyword",
        "search {e} records with a keyword",
        "users can search {es} by {f}",
        "lookup {es} matching a {f}",
        "search for {es} named something",
        "find a {e} with a specific {f}",
        "query {es} by {f}",
        "keyword search on {es}",
        "locate a {e} by {f}",
        "search the {e} list",
        "allow searching {es} by {f} or {f2}",
        "find matching {es} by typing the {f}",
        "look up {es} using a keyword",
        "query the {e} list with a search term",
        "locate {es} matching a keyword",
        "search box to find {es} by {f}",
        "find {es} by {f} or {f2}",
        "users can look up {es} by {f}",
    ],
    "FILTER": [
        "find {es} under {n}",
        "filter {es} by {f}",
        "show {es} with {f} greater than {n}",
        "get {es} where {f} is below {n}",
        "list {es} with {f} between {n} and {n2}",
        "only show {es} that have {f} above {n}",
        "filter {e} records by {f} and {f2}",
        "show only active {es}",
        "get {es} whose {f} is less than {n}",
        "users can filter {es} by {f}",
        "display {es} with {f} equal to {n}",
        "narrow down {es} by {f}",
        "list {es} created after a given date",
        "show {es} having {f} more than {n}",
        "filter the {e} list based on {f}",
        "get {es} in a {f} range",
        "find {es} with {f} under {n}",
        "find {es} above {n}",
        "narrow the {e} list to {f} below {n}",
        "only {es} where {f} is greater than {n}",
        "show only {es} with {f} under {n}",
        "get {es} created before a given date",
    ],
    "SORT": [
        "sort {es} by {f}",
        "order {es} by {f}",
        "arrange {es} in ascending order of {f}",
        "list {es} sorted by {f} descending",
        "sort the {e} list alphabetically",
        "show {es} from highest to lowest {f}",
        "order {e} records by newest first",
        "users can sort {es} by {f}",
        "rank {es} by {f}",
        "arrange {es} by {f} in descending order",
        "sort {es} from lowest to highest {f}",
        "display {es} in order of {f}",
        "order the results by {f}",
        "show latest {es} first",
        "sort {e} records in ascending order",
        "allow sorting of {es} by {f} or {f2}",
        "rank {es} from highest to lowest {f}",
        "arrange the {e} list alphabetically",
        "newest {es} first",
        "list {es} in descending order of {f}",
        "show oldest {es} first",
        "order {es} alphabetically by {f}",
    ],
    "AUTHENTICATION": [
        "users must log in to access {es}",
        "only logged in users can see {es}",
        "add login and signup for the {e} api",
        "register a new user account",
        "users should sign in with email and password",
        "protect the {e} endpoints with authentication",
        "add jwt authentication to the {e} api",
        "users can sign up and log in",
        "require a password to access {es}",
        "secure the {e} api with token based login",
        "add user registration and login",
        "only authorized users can manage {es}",
        "users should be able to log out",
        "authenticate users before they use the {e} api",
        "add a login system with username and password",
        "restrict {e} access to registered users",
        "verify user credentials",
        "implement sign in and sign out",
        "protect {es} with a password",
        "secure login for the {e} api",
        "restrict the api to authorized accounts",
        "check credentials with a token",
        "account registration with email and password",
        "the {e} api needs authentication",
    ],
}

ENTITIES_PER_PATTERN = 4


def fill(pattern: str, entity: str) -> str:
    f, f2 = random.sample(FIELDS, 2)
    n = random.choice([10, 18, 50, 100, 500, 1000, 5000, 50000])
    return pattern.format(e=entity, es=ENTITIES[entity], f=f, f2=f2, n=n, n2=n * 2)


def main() -> None:
    rows, seen = [], set()
    pattern_id = 0
    for intent, patterns in PATTERNS.items():
        for pattern in patterns:
            pattern_id += 1
            uses_entity = "{e}" in pattern or "{es}" in pattern
            chosen = random.sample(list(ENTITIES), ENTITIES_PER_PATTERN) if uses_entity else ["student"]
            for entity in chosen:
                text = fill(pattern, entity)
                if text in seen:          # skip exact duplicates
                    continue
                seen.add(text)
                rows.append([text, intent, entity if uses_entity else "none", pattern_id])

    out = Path(__file__).resolve().parent / "intent_dataset.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["requirement", "intent", "entity", "pattern_id"])
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows from {pattern_id} patterns -> {out}")
    for intent in PATTERNS:
        print(f"  {intent:<15}{sum(1 for r in rows if r[1] == intent)}")


if __name__ == "__main__":
    main()