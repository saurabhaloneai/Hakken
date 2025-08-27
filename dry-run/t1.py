import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import json
import requests
import math

class SimpleAgent:
    def __init__(self):
        model_name = "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        self.tools = {
            "web_search": self.web_search,
            "calculator": self.calculator,
            "get_weather": self.get_weather
        }
        
        self.tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Math expression to evaluate"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name"}
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

    def web_search(self, query):
        return f"Search results for '{query}': Sample web search result data"
    
    def calculator(self, expression):
        return str(eval(expression.replace("^", "**")))
    
    def get_weather(self, city):
        return f"Weather in {city}: 22°C, sunny"

    def format_messages(self, messages):
        formatted = ""
        for msg in messages:
            if msg["role"] == "user":
                formatted += f"[INST] {msg['content']} [/INST]\n"
            elif msg["role"] == "assistant":
                if "tool_calls" in msg:
                    tool_call = msg["tool_calls"][0]
                    formatted += f"I'll use {tool_call['function']['name']}: {tool_call['function']['arguments']}\n"
                else:
                    formatted += f"{msg['content']}\n"
            elif msg["role"] == "tool":
                formatted += f"Tool result: {msg['content']}\n"
        return formatted

    def generate_response(self, messages):
        prompt = self.format_messages(messages)
        prompt += "\nTools available: " + json.dumps([tool["function"] for tool in self.tool_definitions], indent=2)
        prompt += "\nRespond with either a tool call in JSON format or a final answer:\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)
        return response.strip()

    def parse_tool_call(self, response):
        try:
            if "tool_call" in response.lower() or "{" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end != 0:
                    json_str = response[start:end]
                    tool_call = json.loads(json_str)
                    return tool_call
        except:
            pass
        return None

    def execute_tool(self, tool_call):
        tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
        params = tool_call.get("arguments") or tool_call.get("function", {}).get("arguments", {})
        
        if isinstance(params, str):
            params = json.loads(params)
            
        if tool_name in self.tools:
            return self.tools[tool_name](**params)
        return f"Tool {tool_name} not found"

    def run(self, user_message, max_iterations=5):
        messages = [{"role": "user", "content": user_message}]
        
        for i in range(max_iterations):
            response = self.generate_response(messages)
            tool_call = self.parse_tool_call(response)
            
            if tool_call:
                result = self.execute_tool(tool_call)
                messages.append({
                    "role": "assistant", 
                    "tool_calls": [{"function": tool_call}]
                })
                messages.append({
                    "role": "tool",
                    "content": result
                })
            else:
                return response
        
        return "Max iterations reached"

# Usage
agent = SimpleAgent()
result = agent.run("What's 15% tip on $50 and what's the weather in Tokyo?")
print(result)

# More examples
print("\n" + "="*50)
print(agent.run("Search for information about Python programming"))

print("\n" + "="*50)  
print(agent.run("Calculate the square root of 144 times 5"))