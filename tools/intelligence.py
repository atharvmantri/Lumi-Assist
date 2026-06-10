"""AI/ML model operations and prompt engineering tools."""
from __future__ import annotations

import json
import time
import concurrent.futures
import requests
import urllib.request
import urllib.parse
import math
import re
from pathlib import Path

from tools import tool


@tool(
    name="run_local_llm",
    description="Execute prompts on local models (Ollama, LM Studio, llama.cpp) for privacy.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The prompt instruction for the local model"},
            "model": {"type": "string", "description": "Model name to request (e.g. 'llama3', 'mistral')", "default": "llama3"},
            "base_url": {"type": "string", "description": "Ollama/local server URL (defaults to http://localhost:11434)", "default": "http://localhost:11434"},
            "system_prompt": {"type": "string", "description": "Optional system context prompt"},
        },
        "required": ["prompt"],
    },
)
def run_local_llm(
    prompt: str,
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    system_prompt: str | None = None,
) -> str:
    url = base_url.rstrip("/")
    
    # Try Ollama endpoint first
    ollama_url = f"{url}/api/generate"
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        t0 = time.perf_counter()
        resp = requests.post(ollama_url, json=payload, timeout=20)
        elapsed = time.perf_counter() - t0
        
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "")
            return f"Ollama ({model}) response in {elapsed:.2f}s:\n\n{response_text}"
    except Exception:
        pass

    # Try standard OpenAI compatible local server (LM Studio, llama.cpp, vllm)
    openai_url = f"{url}/v1/chat/completions"
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        
        t0 = time.perf_counter()
        resp = requests.post(openai_url, json=payload, timeout=20)
        elapsed = time.perf_counter() - t0
        
        if resp.status_code == 200:
            data = resp.json()
            response_text = data["choices"][0]["message"]["content"]
            return f"Local server ({model}) response in {elapsed:.2f}s:\n\n{response_text}"
    except Exception:
        pass

    return (
        f"error: Could not connect to local LLM server at '{base_url}'.\n"
        f"Please verify that either:\n"
        f"  1. Ollama is running (`ollama serve` and model '{model}' is pulled)\n"
        f"  2. LM Studio / llama.cpp / vLLM is hosting a server on that port."
    )


@tool(
    name="embed_text",
    description="Generate numeric vector embeddings for a given text to use in semantic searches.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text string to embed"},
            "model": {"type": "string", "description": "Embedding model name (e.g. 'nomic-embed-text')", "default": "nomic-embed-text"},
            "base_url": {"type": "string", "description": "Ollama server URL for local embedding generation", "default": "http://localhost:11434"},
        },
        "required": ["text"],
    },
)
def embed_text(
    text: str,
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> str:
    url = base_url.rstrip("/")
    
    # 1. Try local Ollama embeddings API
    try:
        resp = requests.post(
            f"{url}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=10,
        )
        if resp.status_code == 200:
            embedding = resp.json().get("embedding", [])
            return json.dumps({
                "source": "ollama",
                "model": model,
                "dimensions": len(embedding),
                "embedding": embedding[:10],
                "note": f"Showing first 10 dimensions out of {len(embedding)}"
            })
    except Exception:
        pass

    # 2. Try primary OpenAI compatible client embeddings API (e.g., LM Studio local v1)
    try:
        resp = requests.post(
            f"{url}/v1/embeddings",
            json={"model": model, "input": text},
            timeout=10,
        )
        if resp.status_code == 200:
            embedding = resp.json()["data"][0]["embedding"]
            return json.dumps({
                "source": "local_openai",
                "model": model,
                "dimensions": len(embedding),
                "embedding": embedding[:10],
                "note": f"Showing first 10 dimensions out of {len(embedding)}"
            })
    except Exception:
        pass

    # 3. Fallback: Generate local bag-of-words / pseudo-embedding vector
    # This guarantees the tool always returns a vector even without server dependencies.
    words = re.findall(r"\b\w{3,}\b", text.lower())
    # Create simple deterministic hash-based 64-dimensional float vector
    vec = [0.0] * 64
    for w in words:
        # Deterministic hashing to map word to vector index
        val = sum(ord(char) for char in w)
        idx = val % 64
        vec[idx] += 1.0
        
    # L2 normalization
    sq_sum = sum(x*x for x in vec)
    if sq_sum > 0:
        norm = math.sqrt(sq_sum)
        vec = [x/norm for x in vec]
        
    return json.dumps({
        "source": "fallback_lexical_hashing",
        "model": "pseudo-embeddings-64",
        "dimensions": 64,
        "embedding": vec[:10],
        "note": "Fallback pseudo-embedding vector generated successfully."
    })


@tool(
    name="fine_tune_model",
    description="Train a local PyTorch classification model on custom prompt-label datasets.",
    parameters={
        "type": "object",
        "properties": {
            "dataset_path": {"type": "string", "description": "Path to JSON dataset file containing text-label pairs (e.g., [{'text': 'hello', 'label': 0}, ...])"},
            "epochs": {"type": "integer", "description": "Number of training epochs (default 5)", "default": 5},
            "learning_rate": {"type": "number", "description": "Learning rate (default 0.01)", "default": 0.01},
            "output_model_path": {"type": "string", "description": "Path to save fine-tuned model checkpoint (defaults to models/fine_tuned_classifier.pt)"},
        },
        "required": ["dataset_path"],
    },
)
def fine_tune_model(
    dataset_path: str,
    epochs: int = 5,
    learning_rate: float = 0.01,
    output_model_path: str | None = None,
) -> str:
    epochs = max(1, min(epochs, 100))
    learning_rate = max(0.0001, min(learning_rate, 0.5))
    
    path = Path(dataset_path)
    if not path.is_file():
        return f"error: dataset file not found: {dataset_path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    except Exception as e:
        return f"error loading dataset: {e}"

    if not isinstance(dataset, list) or not dataset:
        return "error: dataset must be a non-empty list of text-label dictionaries."

    # Parse dataset
    texts = []
    labels = []
    for idx, item in enumerate(dataset):
        if "text" not in item or "label" not in item:
            return f"error: dataset item at index {idx} must contain 'text' and 'label' keys."
        texts.append(str(item["text"]))
        labels.append(int(item["label"]))

    num_classes = len(set(labels))
    if num_classes < 2:
        return "error: training dataset must have at least 2 distinct classes."

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
    except ImportError:
        return "error: PyTorch is required for local fine-tuning. Run `pip install torch`."

    # Preprocessing: Construct vocab list
    import re
    vocab = set()
    for t in texts:
        words = re.findall(r"\b\w{3,}\b", t.lower())
        vocab.update(words)
    
    vocab_list = sorted(list(vocab))
    vocab_size = len(vocab_list)
    if vocab_size == 0:
        return "error: vocab size is 0. Check text length and formatting."
        
    vocab_index = {w: i for i, w in enumerate(vocab_list)}

    # Convert texts to tensors (bag of words representations)
    def text_to_tensor(text_str: str) -> torch.Tensor:
        tensor = torch.zeros(vocab_size)
        words = re.findall(r"\b\w{3,}\b", text_str.lower())
        for w in words:
            if w in vocab_index:
                tensor[vocab_index[w]] += 1.0
        return tensor

    x_data = torch.stack([text_to_tensor(t) for t in texts])
    y_data = torch.tensor(labels, dtype=torch.long)

    # Define a simple PyTorch model
    class SimpleClassifier(nn.Module):
        def __init__(self, input_dim, output_dim):
            super().__init__()
            self.linear = nn.Linear(input_dim, output_dim)
            
        def forward(self, x):
            return self.linear(x)

    model = SimpleClassifier(vocab_size, num_classes)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        outputs = model(x_data)
        loss = criterion(outputs, y_data)
        loss.backward()
        optimizer.step()
        history.append(loss.item())

    # Save model weights and vocab mapping
    out_path = Path(output_model_path) if output_model_path else Path("models/fine_tuned_classifier.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    torch.save({
        "state_dict": model.state_dict(),
        "vocab": vocab_list,
        "classes": num_classes,
    }, str(out_path))

    return (
        f"Training successfully completed!\n"
        f"  - Vocabulary Size: {vocab_size} unique words\n"
        f"  - Number of Classes: {num_classes}\n"
        f"  - Total Epochs: {epochs}\n"
        f"  - Initial Loss: {history[0]:.4f}\n"
        f"  - Final Loss: {history[-1]:.4f}\n"
        f"  - Saved model checkpoint to: {out_path}"
    )


@tool(
    name="model_benchmark",
    description="Compare speed and quality of response from different AI models on a prompt.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The benchmark prompt string to execute"},
            "models": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of model identifiers to test (e.g. ['meta-llama/Llama-3-70b-instruct', 'microsoft/WizardLM-2-8x22B'])",
            },
        },
        "required": ["prompt"],
    },
)
def model_benchmark(prompt: str, models: list[str] | None = None) -> str:
    from core.llm import LLMClient
    
    # Defaults models via proxy
    target_models = models or [
        "meta-llama/Llama-3-70b-instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ]
    
    results = []

    def query_single_model(model_name: str) -> dict:
        try:
            client = LLMClient()
            client.model = model_name
            
            t0 = time.perf_counter()
            # Send prompt (non-stream)
            response_text = client.complete(prompt)
            elapsed = time.perf_counter() - t0
            
            # Simple token approximation (4 characters = 1 token)
            token_count = len(response_text) // 4
            tokens_per_sec = token_count / elapsed if elapsed > 0 else 0.0
            
            return {
                "model": model_name,
                "status": "success",
                "time_s": elapsed,
                "tokens": token_count,
                "speed": tokens_per_sec,
                "preview": response_text[:100] + "...",
            }
        except Exception as e:
            return {
                "model": model_name,
                "status": "failed",
                "error": str(e),
            }

    # Parallel queries
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_models)) as executor:
        futures = [executor.submit(query_single_model, m) for m in target_models]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # Build benchmark table
    lines = [f"Model Benchmark comparison on prompt: '{prompt}'", ""]
    
    header = f"{'Model':40s} | {'Status':8s} | {'Time (s)':8s} | {'Tokens':6s} | {'Tokens/s':8s}"
    lines.append(header)
    lines.append("-" * len(header))
    
    for r in results:
        if r["status"] == "success":
            lines.append(f"{r['model']:40s} | {'success':8s} | {r['time_s']:8.2f} | {r['tokens']:6d} | {r['speed']:8.1f}")
            lines.append(f"  Preview: {r['preview']}")
        else:
            lines.append(f"{r['model']:40s} | {'failed':8s} | {'N/A':8s} | {'N/A':6s} | {'N/A':8s}")
            lines.append(f"  Error: {r['error']}")
        lines.append("")
        
    return "\n".join(lines).strip()


@tool(
    name="prompt_optimizer",
    description="Analyze and suggest prompt engineering improvements to a draft prompt.",
    parameters={
        "type": "object",
        "properties": {
            "draft_prompt": {"type": "string", "description": "The raw draft prompt text to optimize"},
            "use_case": {"type": "string", "description": "Goal of the prompt (e.g. 'code generation', 'customer support')"},
        },
        "required": ["draft_prompt"],
    },
)
def prompt_optimizer(draft_prompt: str, use_case: str | None = None) -> str:
    from core.llm import LLMClient
    
    meta_prompt = (
        "You are an expert prompt optimizer. Reconstruct the provided draft prompt "
        "according to standard prompt engineering principles (role definition, "
        "clear instructions, contextual bounds, formatting rules, few-shot examples if useful, "
        "and clear demarcations).\n\n"
    )
    if use_case:
        meta_prompt += f"Target Use Case: {use_case}\n"
    meta_prompt += f"Draft Prompt:\n\"\"\"\n{draft_prompt}\n\"\"\"\n\n"
    meta_prompt += "Provide your response as a structured markdown output detailing:\n1. Analysis (limitations of the draft)\n2. Optimized Prompt (inside a code block for copying)\n3. Rationale (what was changed and why)."

    try:
        client = LLMClient()
        response_text = client.complete(meta_prompt)
        return response_text
    except Exception as e:
        return f"error: Failed to contact optimization model: {e}"
