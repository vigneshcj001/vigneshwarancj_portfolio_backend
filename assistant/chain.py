import os
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser
from .prompt import assistant_prompt

llm = Ollama(
    base_url=os.getenv("OLLAMA_BASE_URL"),
    model=os.getenv("OLLAMA_MODEL"),
    temperature=0.2,
)

output_parser = StrOutputParser()

assistant_chain = assistant_prompt | llm | output_parser
