from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict

Kind = Literal["file","function","route","component","test"]

class Node(BaseModel):
    node_id: str
    kind: Kind
    name: str
    path: str
    lang: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    attrs: Dict = Field(default_factory=dict)

class Edge(BaseModel):
    src: str
    dst: str
    type: Literal["imports","calls","ui_event","client_to_route","covers","unknown"]
    attrs: Dict = Field(default_factory=dict)
