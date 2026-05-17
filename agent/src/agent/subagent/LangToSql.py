from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

SqlGeneratorAgent = Agent(
    name="LangToSql_Agent",
    model=LiteLlm(
        model="dashscope/qwen-plus",  # 指定 OpenRouter 模型
        api_key="sk-37c1d3a0ccd748db97e27c5682fd814d",       # 从环境变量中读取 API 密钥
    ),
    description=(
        "You are an agent that can convert natural language queries into SQL queries."
    ),
    instruction=(
        "Given a user's natural language request, generate an appropriate SQL query "
        "to retrieve the requested data from the database. Ensure the SQL syntax is correct."
    ),
)