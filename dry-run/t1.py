import torch
from vllm import LLM, SamplingParams
import json
import math
import re
from Hakken.integrations.search import internet_search, TavilyIntegration

class vLLMAgent:
    def __init__(self, model_name="Qwen/Qwen2.5-7B-Instruct", quantization=None):
        """
        Initialize vLLM Agent with specified model
        
        VRAM Requirements:
        - "microsoft/Phi-3.5-mini-instruct" (3.8B): ~8GB VRAM
        - "Qwen/Qwen2.5-7B-Instruct" (7B): ~14GB VRAM  
        - "meta-llama/Llama-3.1-8B-Instruct" (8B): ~16GB VRAM
        - "Qwen/Qwen2.5-Coder-32B-Instruct" (32B): ~32GB with quantization
        - "meta-llama/Llama-3.1-70B-Instruct" (70B): ~70GB with quantization
        - "deepseek-ai/DeepSeek-V3-Base" (671B MoE): ~80-160GB VRAM
        
        quantization options: None, "awq", "gptq", "squeezellm", "fp8"
        """
        print(f"🚀 Initializing vLLM with model: {model_name}")
        
        # vLLM initialization parameters based on VRAM
        vllm_params = {
            "model": model_name,
            "tensor_parallel_size": 1,  # Increase for multi-GPU setups
            "gpu_memory_utilization": 0.85,  # Use 85% of GPU memory
            "trust_remote_code": True,
            "dtype": "half",  # Use float16 for efficiency
        }
        
        # Add quantization if specified
        if quantization:
            vllm_params["quantization"] = quantization
            print(f"🔧 Using {quantization} quantization to reduce VRAM usage")
        
        # Adjust max_model_len based on available memory and model
        if "phi" in model_name.lower():
            vllm_params["max_model_len"] = 16384  # Phi models
        elif "7b" in model_name.lower() or "8b" in model_name.lower():
            vllm_params["max_model_len"] = 32768  # 7B/8B models
        elif "32b" in model_name.lower():
            vllm_params["max_model_len"] = 24576  # Optimal for 32B on 32GB VRAM
        elif "70b" in model_name.lower():
            vllm_params["max_model_len"] = 12288  # Quantized 70B models
        else:
            vllm_params["max_model_len"] = 16384  # Safe default
        
        # Initialize vLLM engine
        try:
            self.llm = LLM(**vllm_params)
        except Exception as e:
            print(f"❌ Failed to initialize vLLM: {e}")
            print("💡 Try reducing gpu_memory_utilization or max_model_len")
            raise
        
        # Sampling parameters
        self.sampling_params = SamplingParams(
            temperature=0.1,
            top_p=0.9,
            max_tokens=8000,
            repetition_penalty=1.1,
            stop=["<|im_end|>", "<|endoftext|>"]
        )
        
        self.conversation_history = []
        self.model_name = model_name
        
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
                    "description": "Search the web for current information, news, time, dates, real-time data, or any information not in your knowledge base",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query - be specific about what you need"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "calculator",
                    "description": "Perform mathematical calculations, arithmetic, percentages, square roots, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Math expression to evaluate (use sqrt, *, /, +, -, **, etc.)"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather information for a specific city (NOT for time or general country info)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "Specific city name (not country)"}
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

    def web_search(self, query):
        try:
            results = internet_search(query, max_results=3)
            content = []
            for result in results.get("results", [])[:3]:
                content.append(f"Title: {result.get('title', 'N/A')}")
                content.append(f"Content: {result.get('content', 'N/A')[:500]}...")
            return "\n".join(content)
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def calculator(self, expression):
        try:
            # Safe evaluation with basic math operations
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"abs": abs, "round": round})
            
            # Replace common mathematical notation
            expression = expression.replace("^", "**")
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    def get_weather(self, city):
        # Mock weather function - replace with actual API call
        return f"Weather in {city}: 22°C, sunny with light clouds"

    def format_messages_for_chat(self, messages):
        """Format messages for chat template - adapts to different model formats"""
        if "qwen" in self.model_name.lower():
            # Qwen format
            formatted = "<|im_start|>system\nYou are Qwen, created by Alibaba Cloud. You are a helpful assistant.<|im_end|>\n"
        elif "llama" in self.model_name.lower():
            # Llama format
            formatted = "<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are a helpful AI assistant.<|eot_id|>\n"
        elif "deepseek" in self.model_name.lower():
            # DeepSeek format (similar to general format)
            formatted = "<|im_start|>system\nYou are a helpful AI assistant created by DeepSeek.<|im_end|>\n"
        else:
            # Generic format
            formatted = "<|im_start|>system\nYou are a helpful AI assistant.<|im_end|>\n"
        
        for msg in messages[1:]:  # Skip system message as we handle it above
            if "qwen" in self.model_name.lower() or "deepseek" in self.model_name.lower():
                if msg["role"] == "user":
                    formatted += f"<|im_start|>user\n{msg['content']}<|im_end|>\n"
                elif msg["role"] == "assistant":
                    formatted += f"<|im_start|>assistant\n{msg['content']}<|im_end|>\n"
                elif msg["role"] == "tool":
                    formatted += f"<|im_start|>tool\n{msg['content']}<|im_end|>\n"
            elif "llama" in self.model_name.lower():
                if msg["role"] == "user":
                    formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{msg['content']}<|eot_id|>\n"
                elif msg["role"] == "assistant":
                    formatted += f"<|start_header_id|>assistant<|end_header_id|>\n\n{msg['content']}<|eot_id|>\n"
                elif msg["role"] == "tool":
                    formatted += f"<|start_header_id|>tool<|end_header_id|>\n\n{msg['content']}<|eot_id|>\n"
        
        # Add assistant start token
        if "qwen" in self.model_name.lower() or "deepseek" in self.model_name.lower():
            formatted += "<|im_start|>assistant\n"
        elif "llama" in self.model_name.lower():
            formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        else:
            formatted += "<|im_start|>assistant\n"
            
        return formatted

    def create_system_prompt(self):
        return """You are a helpful AI assistant with access to tools. Choose the RIGHT tool for each task:

**web_search**: Use for current/real-time information like:
- search on this URL = "https://www.timeanddate.com/worldclock/" whenever user ask for time 
- be careful with AM and PM 
- can use many iteration to get accurate result
- Current time anywhere in the world
- Today's date, current news, stock prices
- Recent events, current weather conditions
- Any information that changes frequently
- Information you don't have in your knowledge
- Verify you result with multiple sources 

**calculator**: Use for mathematical operations like:
- Percentages, tips, taxes (e.g., "50 * 0.15")  
- Basic math (+, -, *, /, sqrt, etc.)
- Mathematical expressions

**get_weather**: Use ONLY for weather in specific cities:
- "What's the weather in Tokyo?" → get_weather
- "Weather in Mumbai?" → get_weather  
- NOT for time, dates, or general country info

CRITICAL RULES:
1. For time queries → USE WEB_SEARCH with queries like "current time in India"
2. For math → USE CALCULATOR  
3. For city weather → USE GET_WEATHER
4. Respond with ONLY one tool call per response:

TOOL_CALL: {"name": "tool_name", "arguments": {"param": "value"}}

Examples:
- "Current time in India" → TOOL_CALL: {"name": "web_search", "arguments": {"query": "current time in India right now"}}
- "15% of $50" → TOOL_CALL: {"name": "calculator", "arguments": {"expression": "50 * 0.15"}}
- "Weather in Delhi" → TOOL_CALL: {"name": "get_weather", "arguments": {"city": "Delhi"}}

If no tools needed, give a normal response."""

    def generate_response(self, messages):
        # Add system prompt
        full_messages = [
            {"role": "system", "content": self.create_system_prompt()}
        ] + messages
        
        prompt = self.format_messages_for_chat(full_messages)
        
        # Generate with vLLM
        outputs = self.llm.generate([prompt], self.sampling_params)
        response = outputs[0].outputs[0].text.strip()
        
        return response

    def parse_tool_call(self, response):
        """Extract tool call from response"""
        try:
            # Look for TOOL_CALL: pattern - handle incomplete JSON
            tool_pattern = r'TOOL_CALL:\s*(\{[^}]*\}*)'
            match = re.search(tool_pattern, response, re.DOTALL)
            
            if match:
                json_str = match.group(1).strip()
                print(f"🔍 Raw extracted: {json_str}")
                
                # Fix incomplete JSON by ensuring proper closing
                if json_str.count('{') > json_str.count('}'):
                    # Add missing closing braces
                    missing_braces = json_str.count('{') - json_str.count('}')
                    json_str += '}' * missing_braces
                    print(f"🔧 Fixed JSON: {json_str}")
                
                # Try parsing the fixed JSON
                try:
                    tool_call = json.loads(json_str)
                    print(f"✅ Successfully parsed: {tool_call}")
                    return tool_call
                except json.JSONDecodeError:
                    print("🔧 JSON still invalid, trying manual extraction...")
            
            # Manual extraction fallback
            print("🔍 Attempting manual extraction...")
            
            # Extract tool name
            name_match = re.search(r'"name":\s*"([^"]*)"', response)
            if not name_match:
                print("❌ Could not find tool name")
                return None
                
            tool_name = name_match.group(1)
            print(f"🎯 Tool name: {tool_name}")
            
            # Extract arguments - more flexible pattern
            arguments = {}
            
            # Look for the arguments section
            args_section = re.search(r'"arguments":\s*\{([^}]*)', response)
            if args_section:
                args_content = args_section.group(1)
                print(f"🎯 Args content: {args_content}")
                
                # Extract key-value pairs from arguments
                # Handle both quoted and unquoted values
                arg_patterns = [
                    r'"([^"]+)":\s*"([^"]*)"',  # "key": "value"
                    r'"([^"]+)":\s*([^",}]+)',  # "key": value (unquoted)
                ]
                
                for pattern in arg_patterns:
                    matches = re.findall(pattern, args_content)
                    for key, value in matches:
                        arguments[key] = value.strip().strip('"')
                        
            print(f"🎯 Extracted arguments: {arguments}")
            
            if tool_name and arguments:
                tool_call = {
                    "name": tool_name,
                    "arguments": arguments
                }
                print(f"✅ Manually constructed tool call: {tool_call}")
                return tool_call
                
        except Exception as e:
            print(f"❌ Tool parsing error: {e}")
            
        return None

    def execute_tool(self, tool_call):
        """Execute the tool and return results"""
        try:
            tool_name = tool_call.get("name")
            params = tool_call.get("arguments", {})
            
            if isinstance(params, str):
                params = json.loads(params)
                
            if tool_name in self.tools:
                result = self.tools[tool_name](**params)
                return result
            else:
                return f"Error: Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
                
        except Exception as e:
            return f"Tool execution error: {str(e)}"

    def run(self, user_message, max_iterations=10):
        messages = self.conversation_history + [{"role": "user", "content": user_message}]
        
        print(f"🤖 Starting vLLM agent with max {max_iterations} iterations")
        
        for i in range(max_iterations):
            current_iteration = i + 1
            print(f"\n📍 Iteration {current_iteration}/{max_iterations}")
            
            response = self.generate_response(messages)
            print(f"🧠 Model response: {response[:150]}..." if len(response) > 150 else f"🧠 Model response: {response}")
            
            tool_call = self.parse_tool_call(response)
            
            if tool_call:
                print(f"🔧 Using tool: {tool_call.get('name', 'unknown')} with args: {tool_call.get('arguments', {})}")
                
                # Execute the tool
                result = self.execute_tool(tool_call)
                print(f"📊 Tool result: {result[:100]}..." if len(result) > 100 else f"📊 Tool result: {result}")
                
                # Add tool call to conversation
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "tool", "content": f"Tool '{tool_call['name']}' returned: {result}"})
                
            else:
                # No tool call detected, this is the final answer
                print(f"✅ Final answer ready after {current_iteration} iterations")
                
                # Check if the response mentions needing another tool
                needs_more_tools = any(phrase in response.lower() for phrase in [
                    "waiting for", "need to", "let me check", "now for the"
                ])
                
                if needs_more_tools and current_iteration < max_iterations:
                    print("🤔 Response suggests more tools needed, continuing...")
                    # Add a prompt to continue with the next tool
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": "Please continue with the next step or tool needed."})
                    continue
                
                self.conversation_history = messages + [{"role": "assistant", "content": response}]
                return response
        
        print(f"⚠️  Reached max iterations ({max_iterations})")
        self.conversation_history = messages
        return "I've reached the maximum number of iterations. Let me provide what I have so far: " + response
    
    def get_conversation_history(self):
        return self.conversation_history
    
    def clear_conversation_history(self):
        self.conversation_history = []
        print("🗑️  Conversation history cleared")

    def update_sampling_params(self, **kwargs):
        """Update sampling parameters for different use cases"""
        for key, value in kwargs.items():
            if hasattr(self.sampling_params, key):
                setattr(self.sampling_params, key, value)
                print(f"📊 Updated {key} to {value}")

# Usage example
if __name__ == "__main__":
    # Initialize with your preferred model based on your VRAM
    gpu_memory_gb = 24  # Set your actual VRAM here
    
    if gpu_memory_gb >= 80:
        model_choice = "deepseek-ai/DeepSeek-V3-Base"
        quantization = None
    elif gpu_memory_gb >= 48:
        model_choice = "meta-llama/Llama-3.1-70B-Instruct"  
        quantization = "awq"  # Use quantization to fit in 48GB
    elif gpu_memory_gb >= 32:
        model_choice = "Qwen/Qwen2.5-Coder-32B-Instruct"
        quantization = "awq"
    elif gpu_memory_gb >= 16:
        model_choice = "Qwen/Qwen2.5-7B-Instruct"
        quantization = None
    else:
        model_choice = "microsoft/Phi-3.5-mini-instruct"
        quantization = None
    
    print(f"🎯 Selected model for {gpu_memory_gb}GB VRAM: {model_choice}")
    agent = vLLMAgent(model_name=model_choice, quantization=quantization)

    # Test the time query that should use web search
    print("="*60)
    result = agent.run("what is the current time in London right now?")
    print(f"\n🎯 Final Result: {result}")

    # Continue conversation with history
    print("\n" + "="*60)
    result2 = agent.run("What about calculating 20% tip on $50?")
    print(f"\n🎯 Final Result: {result2}")

    # Check conversation history
    print("\n" + "="*60)
    print("📚 Conversation History:")
    for i, msg in enumerate(agent.get_conversation_history()[-6:]):  # Show last 6 messages
        role = msg["role"].upper()
        content = msg.get("content", str(msg))[:100]
        print(f"{i+1}. {role}: {content}...")

    # Clear history and test pure time query
    print("\n" + "="*60)
    agent.clear_conversation_history()
    result3 = agent.run("What time is it in Mumbai right now?")
    print(f"\n🎯 Final Result: {result3}")