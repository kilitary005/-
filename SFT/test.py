from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 加载预训练音乐生成模型
model_name = "microsoft/muzic-transformer"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 生成音乐
prompt = "生成一段欢快的C大调钢琴曲，节奏为中板"
inputs = tokenizer(prompt, return_tensors="pt")

with torch.no_grad():
    outputs = model.generate(
        inputs.input_ids,
        max_length=512,
        temperature=0.9,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )

generated_music = tokenizer.decode(outputs[0], skip_special_tokens=True)

