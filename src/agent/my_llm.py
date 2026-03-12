from langchain_openai import ChatOpenAI
from zhipuai import ZhipuAI

from agent.env_utils import ZHIPU_API_KEY, ZHIPU_BASE_URL, OLLAMA_BASE_URL, OLLAMA_MODEL_NAME

# llm = ChatOpenAI(
#     model="glm-4-flash",
#     api_key=ZHIPU_API_KEY,
#     base_url=ZHIPU_BASE_URL, # 智谱的 Base URL
#     temperature=0.1
# )

# llm = ChatOpenAI(
#     model="glm-4.7-flash",
#     api_key=ZHIPU_API_KEY,
#     base_url='http://localhost:11434/v1', # Ollama 的 Base URL
#     temperature=0.1
# )

llm = ChatOpenAI(
    model=OLLAMA_MODEL_NAME,
    api_key=ZHIPU_API_KEY,
    base_url=OLLAMA_BASE_URL, # Ollama 的 Base URL
    temperature=0.1
)

# zhipuai_client = ZhipuAI(
#     api_key=ZHIPU_API_KEY,
#     base_url=ZHIPU_BASE_URL  # 智谱的 Base URL
# )