# Complete Research Agent Function Breakdown

## Core Architecture Components

### 1. Agent Framework Components
- **DeepAgent Class**: Main agent orchestrator
- **SubAgent Class**: Individual specialized agents
- **Agent State Management**: Tracks conversation, files, and execution state
- **Tool Registry**: Manages available tools and their execution
- **Message Routing**: Routes messages between main agent and sub-agents
- **Recursion Management**: Handles nested agent calls with limits

### 2. File System Operations
```python
# File operations needed:
def write_file(filename: str, content: str)
def read_file(filename: str) -> str
def file_exists(filename: str) -> bool
def create_directory(path: str)
def list_files(directory: str = ".") -> List[str]
```

### 3. Internet Search Integration
```python
# Tavily client wrapper functions:
def initialize_tavily_client(api_key: str) -> TavilyClient
def search_web(query: str, max_results: int, topic: str, include_raw_content: bool) -> Dict
def format_search_results(results: Dict) -> str
def extract_urls_from_results(results: Dict) -> List[str]
def extract_content_from_results(results: Dict) -> List[Dict]
```

## Agent Communication System

### 4. Message Processing
```python
class Message:
    def __init__(self, role: str, content: str, timestamp: datetime)
    def to_dict(self) -> Dict
    def from_dict(cls, data: Dict) -> 'Message'

class MessageHistory:
    def __init__(self)
    def add_message(self, message: Message)
    def get_messages(self) -> List[Message]
    def clear_history(self)
    def get_context(self, max_tokens: int) -> str
```

### 5. Sub-Agent Management
```python
class SubAgentManager:
    def __init__(self, subagents: List[Dict])
    def register_subagent(self, config: Dict)
    def get_subagent(self, name: str) -> SubAgent
    def execute_subagent(self, name: str, prompt: str, tools: List[str]) -> str
    def route_to_subagent(self, agent_name: str, message: str) -> str
```

### 6. Tool Execution System
```python
class ToolRegistry:
    def __init__(self)
    def register_tool(self, name: str, function: callable, description: str)
    def get_tool(self, name: str) -> callable
    def execute_tool(self, name: str, **kwargs) -> Any
    def list_available_tools(self) -> List[str]
    def get_tool_schema(self, name: str) -> Dict
```

## LLM Integration Layer

### 7. LLM Communication
```python
class LLMClient:
    def __init__(self, api_key: str, model: str, base_url: str)
    def generate_response(self, messages: List[Dict], tools: List[Dict] = None) -> str
    def parse_tool_calls(self, response: str) -> List[Dict]
    def format_messages(self, history: MessageHistory) -> List[Dict]
    def handle_function_calling(self, response: str) -> Tuple[str, List[Dict]]
```

### 8. Prompt Management
```python
class PromptManager:
    def __init__(self)
    def create_system_prompt(self, base_prompt: str, tools: List[str], context: str) -> str
    def format_research_prompt(self, question: str, context: str) -> str
    def format_critique_prompt(self, report_content: str, question: str) -> str
    def add_tool_descriptions(self, prompt: str, tools: List[Dict]) -> str
    def create_subagent_prompt(self, subagent_config: Dict, context: str) -> str
```

## Research Workflow Components

### 9. Research Planning
```python
class ResearchPlanner:
    def __init__(self)
    def analyze_question(self, question: str) -> Dict
    def create_research_plan(self, question: str) -> List[str]
    def identify_subtopics(self, question: str) -> List[str]
    def prioritize_research_areas(self, areas: List[str]) -> List[str]
    def estimate_research_depth(self, question: str) -> int
```

### 10. Report Generation
```python
class ReportGenerator:
    def __init__(self)
    def create_report_structure(self, question: str, research_data: List[Dict]) -> Dict
    def format_markdown_report(self, sections: List[Dict]) -> str
    def add_citations(self, content: str, sources: List[Dict]) -> str
    def validate_report_format(self, report: str) -> bool
    def extract_sources_from_content(self, content: str) -> List[str]
```

### 11. Citation Management
```python
class CitationManager:
    def __init__(self)
    def track_sources(self, url: str, title: str, content: str)
    def generate_citation_number(self, url: str) -> int
    def format_citation(self, source: Dict, number: int) -> str
    def create_sources_section(self) -> str
    def validate_citations(self, content: str) -> List[str]
```

## State Management

### 12. Agent State
```python
class AgentState:
    def __init__(self)
    def set_current_question(self, question: str)
    def get_current_question(self) -> str
    def add_research_data(self, data: Dict)
    def get_research_data(self) -> List[Dict]
    def set_report_status(self, status: str)
    def track_subagent_calls(self, agent_name: str, result: str)
    def get_execution_history(self) -> List[Dict]
```

### 13. Configuration Management
```python
class ConfigManager:
    def __init__(self, config: Dict)
    def get_recursion_limit(self) -> int
    def get_max_research_iterations(self) -> int
    def get_llm_settings(self) -> Dict
    def get_search_settings(self) -> Dict
    def validate_config(self) -> bool
```

## Error Handling & Logging

### 14. Error Management
```python
class ErrorHandler:
    def __init__(self)
    def handle_api_error(self, error: Exception) -> str
    def handle_file_error(self, error: Exception) -> str
    def handle_tool_error(self, tool_name: str, error: Exception) -> str
    def log_error(self, error: Exception, context: str)
    def retry_operation(self, operation: callable, max_retries: int) -> Any
```

### 15. Logging System
```python
class AgentLogger:
    def __init__(self, log_level: str)
    def log_agent_action(self, action: str, details: Dict)
    def log_tool_execution(self, tool_name: str, params: Dict, result: Any)
    def log_subagent_call(self, agent_name: str, input_msg: str, output_msg: str)
    def log_research_progress(self, step: str, status: str)
    def export_execution_log(self) -> Dict
```

## Main Agent Orchestration

### 16. Core Agent Class
```python
class ResearchAgent:
    def __init__(self, tools: List[callable], instructions: str, subagents: List[Dict])
    def process_user_input(self, input_text: str) -> str
    def execute_research_workflow(self, question: str) -> str
    def coordinate_subagents(self, research_plan: List[str]) -> List[str]
    def generate_final_report(self, research_results: List[str]) -> str
    def critique_and_refine_report(self, report: str) -> str
    def run(self, user_input: str) -> str
```

### 17. Workflow Orchestration
```python
class WorkflowManager:
    def __init__(self, agent: ResearchAgent)
    def execute_research_phase(self, question: str) -> List[Dict]
    def execute_writing_phase(self, research_data: List[Dict]) -> str
    def execute_critique_phase(self, report: str, question: str) -> Dict
    def execute_refinement_phase(self, report: str, critique: Dict) -> str
    def check_completion_criteria(self, report: str, critique: Dict) -> bool
```

## Integration Points

### 18. External Service Integrations
```python
# Tavily Search Integration
class TavilyIntegration:
    def __init__(self, api_key: str)
    def search(self, query: str, **kwargs) -> Dict
    def get_search_context(self, results: Dict) -> str
    def extract_key_information(self, results: Dict) -> List[str]

# LLM Provider Integration
class LLMProviderIntegration:
    def __init__(self, provider: str, api_key: str, model: str)
    def call_llm(self, messages: List[Dict], **kwargs) -> str
    def handle_rate_limits(self, func: callable) -> Any
    def validate_response(self, response: str) -> bool
```

## Data Models

### 19. Core Data Structures
```python
@dataclass
class ResearchResult:
    query: str
    sources: List[Dict]
    content: str
    timestamp: datetime
    confidence_score: float

@dataclass
class SubAgentConfig:
    name: str
    description: str
    prompt: str
    tools: List[str]
    max_iterations: int

@dataclass
class ReportSection:
    title: str
    content: str
    sources: List[str]
    subsections: List['ReportSection']
```

### 20. Utility Functions
```python
# Text Processing
def clean_text(text: str) -> str
def extract_keywords(text: str) -> List[str]
def summarize_content(content: str, max_length: int) -> str
def detect_language(text: str) -> str
def translate_if_needed(text: str, target_language: str) -> str

# Validation
def validate_markdown(content: str) -> bool
def validate_urls(urls: List[str]) -> List[str]
def validate_report_structure(report: str) -> Dict
def check_citation_format(citations: List[str]) -> bool

# File Processing
def safe_filename(name: str) -> str
def backup_file(filename: str) -> str
def merge_reports(reports: List[str]) -> str
```

## Key Dependencies & Libraries Needed

### 21. Required Libraries
```python
# Core libraries
import os, json, asyncio, datetime, logging, re, typing
from dataclasses import dataclass
from pathlib import Path

# External libraries you'll need
import requests  # For HTTP calls to LLM APIs
import markdown  # For markdown processing
import tavily     # For search (or alternative search APIs)
```

## Execution Flow Functions

### 22. Main Execution Pipeline
```python
def initialize_agent(config: Dict) -> ResearchAgent
def parse_user_question(input_text: str) -> str
def create_research_plan(question: str) -> List[str]
def execute_parallel_research(plan: List[str]) -> List[ResearchResult]
def synthesize_research_results(results: List[ResearchResult]) -> str
def generate_structured_report(synthesis: str, question: str) -> str
def critique_report_quality(report: str, question: str) -> Dict
def refine_report_based_on_critique(report: str, critique: Dict) -> str
def finalize_and_format_report(report: str) -> str
```

This breakdown covers every function, class, and component you'd need to build this research agent from scratch in raw Python, following the same architecture and capabilities as the DeepAgent framework version.