from pydantic import BaseModel

class ContentProcessingPipeline(BaseModel):
    pass

class ContentProcessor(BaseModel):
    pass

class FileContent(BaseModel):
    content: str
    source_url: str
    title: str = ""

class ScrapedContent(BaseModel):
    content: str
    source_url: str
    metadata: dict = {}