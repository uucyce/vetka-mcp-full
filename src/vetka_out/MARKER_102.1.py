class FileReadRequest(BaseModel):
    file_path: str
    marker: str | None = None  # e.g., "MARKER_SCOUT_1"
    context_lines: int = 20

class FileWriteRequest(BaseModel):
    file_path: str
    content: str
    mode: str = "create"  # "create", "patch", "append"