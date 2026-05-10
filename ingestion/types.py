from typing import TypedDict


class Document(TypedDict):
    id: str
    text: str
    article_number: str
    title: str
    regulation: str
    chapter: str
