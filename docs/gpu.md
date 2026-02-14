# GPU Acceleratie

## Vereisten
- NVIDIA GPU (Ampere of nieuwer)
- CUDA Toolkit 12.1
- Python 3.11
- llama-cpp-python 0.3.4 (cu121)

## Installatie

```bash
py -3.11 -m venv venv311
venv311\Scripts\activate
pip install llama-cpp-python==0.3.4 --only-binary=llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

## Model downloaden

```bash
curl -L -o "C:/models/phi3.Q4_K_M.gguf" \
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
```

## Pipeline draaien

```bash
python -m danny_toolkit.pipelines.rag_gpu
```

## Benchmarks (RTX 3060 Ti)

| Metric | Waarde |
|--------|--------|
| Snelheid | 30 tokens / 243 ms |
| VRAM model | ~2.2 GiB |
| KV-cache | ~768 MiB |
| Totale VRAM | ~3.0 GiB |
| Layers offloaded | 33/33 |
