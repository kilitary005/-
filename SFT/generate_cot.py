import os
import pandas as pd
from litellm import completion
from openai import OpenAI
import openai
import json

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="",
    base_url=""
)
# 输出文件路径（提前定义以便在异常处理中使用）
atel = pd.read_csv("atel_output_260202.csv")
out_path = "training_data.jsonl"
#circular = pd.read_csv("circular_output_260202.csv")
print(atel.shape)
#df = pd.read_parquet("hf://datasets/CaraJ/MME-CoT/MME-CoT.parquet")
#df.to_csv("MME-CoT.csv", index=False)
#print(df.head())
for j in range(75, atel.shape[0]):
    payload_parts = ["根据现象进行分析："]
    for i in range(0, len(atel.columns)):
        val = str(atel[atel.columns[i]][j])
        payload_parts.append(val)
        #print(val)
    payload = " ".join(payload_parts)
    print(payload)
    try:
        completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant. 不要加乱七八糟的表情包和你自己的自言自语和总结，我只要分析的文本，我要用于CoT微调，记得要用中文,还有需要明确分步骤，例如：步骤1：识别关键观测事实，步骤2：分析对称边带的含义，步骤3：分析不对称边带的挑战，步骤4：评估理论模型，最终结论"},
        {"role": "user", "content": payload},
    ],
        )
    except openai.BadRequestError as e:
        print("Request blocked by content inspection:", e)
        # 对被审查的数据写入占位响应并继续下一个条目
        instruction = "根据现象分析"
        data = {
            "instruction": instruction,
            "input": payload,
            "response": "[FILTERED_BY_CONTENT_POLICY]"
        }
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
        print("Saved filtered to", out_path)
        continue
    # 尝试把回复解析为 dict，然后提取 content 并追加保存到文件
    try:
        resp = completion.model_dump()
    except Exception:
        import json
        resp = json.loads(completion.model_dump_json())

    content = None
    if isinstance(resp, dict):
        choices = resp.get("choices") or []
        if choices:
            first = choices[0]
            if isinstance(first, dict):
                msg = first.get("message") or first
                if isinstance(msg, dict):
                    content = msg.get("content") or msg.get("text")
            elif isinstance(first, str):
                content = first

    if not content:
        try:
            content = completion.choices[0].message.content
        except Exception:
            content = str(resp)

    if content is None:
        content = ""

    # 保存为 JSON 格式
    instruction = "根据现象分析"
    data = {
        "instruction": instruction,
        "input": payload,
        "response": content.strip()
    }
    
    out_path = "training_data_next.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

    print("Saved to", out_path)
    print("Response:", content)
    




'''
# 获取 API key（优先从环境变量读取，避免在代码中硬编码）
key = os.getenv("QWEN_KEY") or os.getenv("OPENAI_API_KEY")
if not key:
    raise RuntimeError(
        "未找到 API key。请在环境变量中设置 QWEN_KEY 或 OPENAI_API_KEY，然后重试。"
    )
os.environ["OPENAI_API_KEY"] = key

response = completion(
    model="dashscope/qwen-plus",
    messages=[{"content": "Hello, how are you?", "role": "user"}]
)





print(completion.model_dump_json())'''