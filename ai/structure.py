from pydantic import BaseModel, Field, field_validator
import re

class Structure(BaseModel):
    tldr: str = Field(description="one-sentence core innovation summary")
    motivation: str = Field(description="short motivation, empty string if unknown")
    method: str = Field(description="short method description, empty string if unknown")
    result: str = Field(description="short key result, empty string if unknown")
    conclusion: str = Field(description="short conclusion, empty string if unknown")