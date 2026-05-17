import sys
import os
import json
import traceback
from pathlib import Path
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
# 修复导入路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from agent.agent import root_agent
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai.types import Content, Part
    from dotenv import load_dotenv
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"Python路径: {sys.path}")
    raise

load_dotenv()

APP_NAME = "Astronomy_Agent"

# --- Services and Runner Setup ---
session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME, 
    agent=root_agent, 
    session_service=session_service
)

app = FastAPI(title="Astronomy_Agent Chat Interface")

# 创建静态文件目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

# Serve static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 定义请求模型
class ChatRequest(BaseModel):
    query: str

def parse_request_body(body_bytes: bytes) -> dict:
    """解析请求体，支持多种格式"""
    if not body_bytes:
        raise ValueError("Empty request body")
    
    body_str = body_bytes.decode('utf-8').strip()
    print(f"原始请求体字符串: '{body_str}'")
    
    # 去除可能的多余引号
    if body_str.startswith("'") and body_str.endswith("'"):
        body_str = body_str[1:-1]
    elif body_str.startswith('"') and body_str.endswith('"'):
        body_str = body_str[1:-1]
    
    print(f"清理后的字符串: '{body_str}'")
    
    # 方法1: 尝试标准JSON解析
    try:
        if body_str.startswith('{') and body_str.endswith('}'):
            return json.loads(body_str)
    except json.JSONDecodeError:
        pass
    
    # 方法2: 如果是简单字符串，直接作为query
    if body_str and not body_str.startswith('{'):
        return {"query": body_str}
    
    # 方法3: 尝试处理JavaScript对象字面量格式
    try:
        # 处理 {query:value} 格式
        import re
        # 添加双引号到键
        body_str = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*):', r'"\1":', body_str)
        # 为没有引号的值添加双引号（排除数字、布尔值等）
        body_str = re.sub(r':\s*([^",{}\[\]\s][^,}]*)(?=\s*[,}])', r':"\1"', body_str)
        
        print(f"转换后的JSON: '{body_str}'")
        return json.loads(body_str)
    except json.JSONDecodeError as e:
        print(f"JSON转换失败: {e}")
    
    raise ValueError(f"无法解析请求体: {body_str}")

# see the full content below


# --- Web UI Endpoint ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    return FileResponse(Path(__file__).parent / "template" / "chat.html")

@app.post("/chat")
async def chat_endpoint(request: Request):
    """处理聊天请求 - 支持多种请求格式"""
    print("=== 收到聊天请求 ===")
    
    try:
        # 读取请求体
        body_bytes = await request.body()
        print(f"请求体原始字节: {body_bytes}")
        
        # 解析请求体
        body = parse_request_body(body_bytes)
        print(f"解析后的数据: {body}")
        
        query = body.get("query", "").strip()
        print(f"用户查询: '{query}'")
        
        if not query:
            return JSONResponse(content={"response": "Please provide a query."})
        
        # 硬编码的用户和会话ID（演示用）
        user_id = "demo_user"
        session_id = "demo_session"
        
        print("检查会话...")
        # 确保会话存在 - 使用关键字参数
        session = await session_service.get_session(
            app_name=APP_NAME, 
            user_id=user_id, 
            session_id=session_id
        )
        if not session:
            print("创建新会话...")
            session = await session_service.create_session(
                app_name=APP_NAME, 
                user_id=user_id, 
                session_id=session_id
            )
        else:
            print("使用现有会话")
        
        print("开始运行agent...")
        response_text = ""
        event_count = 0
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=query)]),
        ):
            event_count += 1
            print(f"事件 #{event_count}: {event.__class__.__name__}")
            
            if hasattr(event, 'is_final_response') and event.is_final_response():
                print("收到最终响应事件")
                if event.content and event.content.parts:
                    print(f"内容部分数量: {len(event.content.parts)}")
                    for i, part in enumerate(event.content.parts):
                        print(f"部分 {i}: 类型={part.__class__.__name__}")
                        if hasattr(part, "text") and part.text:
                            response_text += part.text
                            print(f"提取的文本: {part.text[:100]}...")
        
        print(f"最终响应文本: '{response_text}'")
        print(f"处理了 {event_count} 个事件")
        
        if not response_text:
            response_text = "I received your message but didn't generate a response. This might be due to agent configuration."
            print("警告: 没有生成响应文本")
        
        return JSONResponse(content={"response": response_text})
    
    except ValueError as e:
        print(f"请求解析错误: {e}")
        return JSONResponse(
            status_code=400,
            content={"response": f"Invalid request format: {str(e)}"}
        )
    except Exception as e:
        print(f"未处理的异常: {str(e)}")
        print(f"异常详情: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"response": f"An internal error occurred: {str(e)}"}
        )
    
HTML_CONTENT_SQL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
<title>SQL Content</title>
</head>
<body>
  <h1>SQL Content Page</h1>
  <p id="demo">This is a placeholder for SQL content.</p>
  <script>
    document.getElementById("demo").innerHTML = "SQL content will be displayed here.";
  </script> 
  <button onclick="location.reload()">Refresh</button>
  <div style="margin-top: 20px;">
        <h3>下载文件：</h3>
        <a href="/download/mydata.sql" download="mydata.sql">下载 SQL 文件</a><br><br>
        <a href="/download/mydata.txt" download="mydata.txt">下载 TXT 文件</a><br><br>
        <a href="/download/mydata.json" download="mydata.json">下载 JSON 文件</a>
      </div>
</body>
</html>
"""
# --- SQL Content Endpoint ---
@app.get("/sql", response_class=HTMLResponse)
async def get_sql_content():
    '''返回SQL内容的HTML页面'''
    return HTML_CONTENT_SQL

@app.get("/api/query")
async def query_database():
    # 连接数据库
    conn = postgres.connect("database.db")
    cursor = conn.cursor()
    
    # 执行查询
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    
    # 转换为字典列表
    result = [{"id": row[0], "name": row[1]} for row in rows]
    
    # 返回JSON
    return {"data": result}

'''@app.post("/sql")
async def get_sql_content(output):
    '''
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)