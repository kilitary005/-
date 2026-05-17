# Load model directly
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
import swanlab
import json
import os
import pandas as pd
from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset

# 检查 GPU 是否可用
print(f"GPU Available: {torch.cuda.is_available()}")
print(f"GPU Count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"Current GPU: {torch.cuda.get_device_name(0)}")

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", device_map="auto")
print(f"Model device: {next(model.parameters()).device}")
train_data = pd.read_json("training_data.jsonl", lines=True)

Prompt_dict = {"prompt_no_input": """<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n<|im_end|>\n<|im_start|>assistant\n""",
    "prompt_input": """<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n{input}<|im_end|>\n<|im_start|>assistant\n"""
    }
print(type(Prompt_dict))

def json_to_dict(inp, out) -> str:
    prompt = Prompt_dict["prompt_input"].format(instruction="请根据现象分析", input=inp, output=out)
    print(prompt)
    return prompt


class SFTDataset(Dataset):
    def __init__(self, data_df, tokenizer, prompt_dict, test_mode=False):
        self.data = data_df
        self.tokenizer = tokenizer
        self.prompt_dict = prompt_dict
        self.test_mode = test_mode
        
        if test_mode and len(data_df) > 0:
            print("测试模式：只使用第一条数据")
            self.test_data = [data_df.iloc[0]]
    
    def __len__(self):
        if self.test_mode:
            return 1  # 测试模式下只有一条数据
        return len(self.data)
    
    def __getitem__(self, idx):
        if self.test_mode:
            row = self.test_data[0]
        else:
            row = self.data.iloc[idx]
        
        instruction = row.get("instruction", "")
        input_text = row.get("input", "")
        output_text = row.get("response", "")
        
        # 构建 prompt
        if input_text:
            prompt = self.prompt_dict["prompt_input"].format(
                instruction=instruction, 
                input=input_text
            )
        else:
            prompt = self.prompt_dict["prompt_no_input"].format(
                instruction=instruction
            )
        
        full_text = prompt + output_text
        
        # tokenize
        encodings = self.tokenizer(
            full_text,
            truncation=True,
            max_length=512,
            padding="max_length",
            return_tensors="pt"
        )
        
        # 获取input_ids
        input_ids = encodings["input_ids"].squeeze()
        
        # 创建labels（初始与input_ids相同）
        labels = input_ids.clone()
        
        # ========== 关键：添加loss掩码 ==========
        # 计算prompt的长度（需要忽略的部分）
        prompt_encoding = self.tokenizer(
            prompt,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        prompt_length = len(prompt_encoding["input_ids"][0])
        
        # 将prompt部分的labels设置为-100（忽略loss）
        labels[:prompt_length] = -100
        
        # ========== 打印调试信息（测试模式）==========
        if self.test_mode and idx == 0:
            print("\n" + "="*50)
            print("📊 测试数据详情：")
            print("="*50)
            print(f"指令: {instruction}")
            print(f"输入: {input_text}")
            print(f"输出: {output_text}")
            print(f"Prompt长度: {prompt_length} tokens")
            print(f"总长度: {len(input_ids)} tokens")
            print(f"需要学习的部分: {len(input_ids) - prompt_length} tokens")
            
            # 查看token化结果
            print("\n🔍 Token分解：")
            for i, token_id in enumerate(input_ids):
                token = self.tokenizer.decode([token_id])
                label = labels[i]
                mask_status = "❌ 掩码" if label == -100 else "✅ 学习"
                print(f"位置 {i:3d}: {token:15s} (ID: {token_id:6d}) - {mask_status}")
            
            print("="*50 + "\n")
        
        return {
            "input_ids": input_ids,
            "attention_mask": encodings["attention_mask"].squeeze(),
            "labels": labels
        }
   

'''print("\n=== Qwen2.5 交互式问答 ===")
print("输入 'exit' 或 'quit' 退出\n")

while True:
    user_input = input("你: ").strip()
    
    if user_input.lower() in ['exit', 'quit', 'q']:
        print("退出对话，再见！")
        break
    
    if not user_input:
        continue
    
    try:
        messages = [
            {"role": "user", "content": user_input},
        ]
        
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)

        outputs = model.generate(**inputs, max_new_tokens=2560, do_sample=True, temperature=0.7)
        response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        print(f"Qwen: {response}\n")
    except Exception as e:
        print(f"错误: {e}\n")
'''

if __name__ == "__main__":
    lora_config = LoraConfig(
        r=16,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.1,
        bias="none",
    )
    # 创建数据集
    train_dataset = SFTDataset(train_data, tokenizer, Prompt_dict, test_mode=True)
    
    model = get_peft_model(model, lora_config)
    print(model)
    model.print_trainable_parameters()
    print(model)
    args = TrainingArguments(
        report_to="none",
        output_dir="outputs",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_train_epochs=5,
        learning_rate=5e-4,
        lr_scheduler_type="constant",
        logging_steps=1,
        save_steps=5,
        remove_unused_columns=False
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset
    )

    trainer.train()

    messages = [
            {"role": "user", "content": "你知道QPOs in 4U 1626-67在1997-12-17有什么现象吗"},
        ]
        
    inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)

    outputs = model.generate(**inputs, max_new_tokens=2560, do_sample=True, temperature=0.7)
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
    print(f"Qwen: {response}\n")