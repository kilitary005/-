import os
import json
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .bge import *
import psycopg2
import pandas as pd

root_agent = Agent(
    name="weather_time_agent",
    model=LiteLlm(
        model="dashscope/qwen3-235b-a22b",  # 指定 OpenRouter 模型
        api_key="sk-37c1d3a0ccd748db97e27c5682fd814d",       # 从环境变量中读取 API 密钥
    ),
    description=(
        "You are an agent that can answer questions about cybersecurity and programming."
    ),
    instruction=(
        "You have access to the following tools: google_search_tool. Use them to answer the user's questions."
    ),
      # 确保 tools 列表中包含所有需要的工具
)