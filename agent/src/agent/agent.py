import os
import json
import psycopg2
import pandas as pd
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .tools import explore_database_structure
from .subagent.LangToSql import SqlGeneratorAgent


# === 配置常量 ===
connection_string = "postgresql://wxuser:wxpass@localhost:5432/wxdb"

# === 先创建模型 ===
model = LiteLlm(
    model="dashscope/qwen-plus",  # 使用阿里云支持的模型
    api_key="sk-37c1d3a0ccd748db97e27c5682fd814d",  # 你的DashScope API Key
)



def format_sql_results(df: pd.DataFrame, sql_query: str = "") -> str:
    """
    格式化SQL查询结果为易读的字符串
    
    Args:
        df: 包含查询结果的DataFrame
        sql_query: 原始SQL查询语句（用于显示）
    
    Returns:
        格式化后的结果字符串
    """
    try:
        # 创建输出缓冲区
        output_parts = []
        
        # 1. 显示查询信息（如果提供了SQL）
        if sql_query:
            output_parts.append(f"🔍 执行的查询:\n{sql_query}\n")
        
        # 2. 显示结果概览
        output_parts.append(f"📊 结果概览: 共 {len(df)} 条记录, {len(df.columns)} 个字段\n")
        
        # 3. 处理列名显示（长列名截断）
        display_columns = []
        for col in df.columns:
            if len(col) > 25:
                display_columns.append(col[:22] + "...")
            else:
                display_columns.append(col)
        
        # 4. 构建表格格式
        rows = []
        
        # 表头
        header = " | ".join(f"{col:>20}" for col in display_columns)
        rows.append(header)
        rows.append("-" * len(header))
        
        # 数据行
        for _, row in df.iterrows():
            row_data = []
            for col in df.columns:
                value = row[col]
                
                # 处理不同类型的值
                if pd.isna(value):
                    formatted_value = "NULL"
                elif isinstance(value, (int, float)):
                    # 数字类型右对齐
                    if isinstance(value, float):
                        formatted_value = f"{value:>15.4f}"
                    else:
                        formatted_value = f"{value:>15d}"
                elif isinstance(value, str):
                    # 字符串截断
                    if len(value) > 20:
                        formatted_value = value[:17] + "..."
                    else:
                        formatted_value = f"{value:>20}"
                elif isinstance(value, (list, dict)):
                    # 复杂类型简略显示
                    formatted_value = f"{type(value).__name__}({len(value)})"
                else:
                    formatted_value = str(value)
                    if len(formatted_value) > 20:
                        formatted_value = formatted_value[:17] + "..."
                
                row_data.append(formatted_value)
            
            row_str = " | ".join(row_data)
            rows.append(row_str)
            
            # 限制显示行数，避免输出过长
            if len(rows) >= 25:  # 表头+分隔线+23行数据
                rows.append("... (更多记录已截断)")
                break
        
        # 5. 添加字段统计信息
        output_parts.append("\n".join(rows))
        output_parts.append(f"\n📈 字段统计:")
        
        for col in df.columns:
            non_null_count = df[col].count()
            null_count = len(df) - non_null_count
            unique_count = df[col].nunique()
            
            stats_parts = []
            stats_parts.append(f"非空: {non_null_count}")
            if null_count > 0:
                stats_parts.append(f"空值: {null_count}")
            stats_parts.append(f"唯一值: {unique_count}")
            
            # 数值列的统计
            if pd.api.types.is_numeric_dtype(df[col]):
                if non_null_count > 0:
                    stats_parts.append(f"均值: {df[col].mean():.2f}")
                    stats_parts.append(f"范围: {df[col].min():.2f}~{df[col].max():.2f}")
            
            output_parts.append(f"  - {col}: {', '.join(stats_parts)}")
        
        # 6. 添加数据预览（前几个值的示例）
        output_parts.append(f"\n🔍 数据预览 (前3个非空值):")
        for col in df.columns:
            non_null_values = df[col].dropna().head(3)
            if len(non_null_values) > 0:
                preview_values = []
                for val in non_null_values:
                    if isinstance(val, str) and len(val) > 30:
                        preview_values.append(f"'{val[:27]}...'")
                    else:
                        preview_values.append(f"'{str(val)}'")
                
                output_parts.append(f"  - {col}: {', '.join(preview_values)}")
        
        return "\n".join(output_parts)
        
    except Exception as e:
        return f"❌ 结果格式化失败: {str(e)}\n原始数据形状: {df.shape}"

def connect_db():
    """创建数据库连接"""
    return psycopg2.connect(connection_string)

def generate_csv_from_df(df: pd.DataFrame, filename: str) -> str:
    """将DataFrame保存为CSV文件"""
    csv_path = f"/tmp/{filename}"
    df.to_csv(csv_path, index=False)
    return csv_path

def send_fileTo_frontend(file_path: str, filename: str):
    """将文件发送到前端"""
    if not os.path.exists(file_path):
        return f"❌ 文件 '{filename}' 不存在"
    
    # 这里假设有一个函数可以处理文件发送
    # send_file(file_path, filename)
    return f"✅ 文件 '{filename}' 已发送到前端"


def execute_sql_and_format(sql_query: str) -> str:
    """安全执行SQL并格式化结果"""
    try:
        # 基本的安全检查
        if any(keyword in sql_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT']):
            return "❌ 不允许执行数据修改操作"
        
        if 'LIMIT' not in sql_query.upper():
            sql_query += " LIMIT 50"  # 默认限制结果数量
        
        with psycopg2.connect(connection_string) as conn:
            df = pd.read_sql(sql_query, conn)
            
        if len(df) == 0:
            return "❌ 未找到相关记录"
        
        #generate_csv_from_df(df, "query_results.csv")
        
        # 格式化结果
        return format_sql_results(df, sql_query)
        
    except Exception as e:
        return f"❌ 查询执行失败: {str(e)}"

def execute_astronomy_query(query_description: str) -> str:
    """根据自然语言描述生成相应的sql语句，执行天文数据查询，由你自己生成以后调用这个函数进行查询
    
    Args:
        query_description: 标准的sql查询
    """
    # LLM解析查询描述，生成SQL
    #sql_query = llm_generate_sql(query_description)
    
    # 执行SQL并返回结果
    return execute_sql_and_format(query_description)



    

# === 创建Agent ===
root_agent = Agent(
    name="Astronomy_Agent",  # 改个更合适的名字
    model=model,
    description=(
        "你是一个专业的天文时域警报数据库助手，"
        "能够帮助用户查询和管理各种天文警报数据，"
        "包括GRB事件、X射线暂现源等。"
    ),
    instruction=("接受用户的自然语言查询请求，并生成sql语句，再调用查询工具，"
        "准确找到相关的天文事件记录。"),
        
    tools=
        [FunctionTool(explore_database_structure), 
         FunctionTool(execute_astronomy_query)
         ],
    # 注意：不需要手动传tools参数，ADK会自动发现@tool装饰的函数
)




