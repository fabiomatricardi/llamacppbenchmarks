# 🚀 Llama.cpp speed Benchmarker

A lightweight, automated Python tool designed to benchmark multiple GGUF models using `llama-cli.exe`. This app helps you find the "sweet spot" between model quantization (BPW) and inference speed (Tokens per Second) on your specific hardware.

> this is the code of my Medium series **"Not All Quantizations Are Born Equal"**


<img src='https://github.com/fabiomatricardi/llamacppbenchmarks/raw/main/lcpp-benchmarks.gif' width=1000>

## ✨ Key Features

* **Automated Batch Testing:** Point it at a folder, and it tests every `.gguf` model it finds.
* **Smart Resource Detection:** Automatically detects your available RAM and CPU threads using `psutil`.
* **Optimal Threading:** Configures tests to use $Threads - 1$ to keep your system responsive.
* **Beautiful Visuals:** Uses `Rich` to render Markdown tables, progress bars, and a "Winner's Podium" directly in your terminal.
* **Multi-format Export:** Saves results to `.json`, `.csv`, and `.md` for easy sharing or analysis.

---

## 🛠️ Requirements

1. **Python 3.10+**
2. **llama-cli.exe**: This script expects the executable to be in the same folder. Donwload the [full binary ZIP archive from llama.cpp](https://github.com/ggml-org/llama.cpp/releases/download/b8287/llama-b8287-bin-win-cpu-x64.zip) un unzip it in the main project directory
3. **Dependencies**:
```bash
pip install rich psutil

```



---

## 🚀 How to Use

1. Place your `.gguf` models in a folder (default is `.\models`).
2. Run the script:
```bash
python lcpp_benchmarking.py --folder .\your_model_path --output my_results

```

In my case I used like this:
```bash
python .\lcpp_benchmarking.py --folder .\models --output results.json

```


3. **The Pre-Flight Check:** The app will show your system specs and the list of models found. Type `y` to start the engine!

---

## 🔍 How it Works (Under the Hood)

### 1. Resource Sensing (`get_system_info`)

Before running any tests, the app uses the `psutil` library to check your hardware. It calculates the **Optimal Threads** for the `-t` parameter. If you have 16 logical cores, it will use 15, ensuring your PC doesn't "freeze" during the benchmark.

### 2. The Benchmark Loop (`run_model_in_folder`)

The script iterates through your folder. For each model, it triggers a `subprocess` to run `llama-cli.exe`. We use a fixed prompt to keep the "race" fair for all models:

> *"explain in simple terms the difference between CPU and GPU during inference"*

### 3. Intelligent Parsing (`extract_speeds_and_bpw`)

Not all versions of `llama.cpp` output text the same way. This function uses **Regular Expressions (Regex)** to find speed data in two ways:

* **Simple Format:** `[ Prompt: 7.6 t/s | Generation: 4.3 t/s ]`
* **Verbose Format:** Standard `llama.cpp` performance logs.
It also captures the **BPW** (Bits Per Weight) from the metadata to show you how compressed the model is.

### 4. Data Export & Visualization

* **Markdown Table:** A clean table sorted by the fastest **Prompt Speed**.
* **Winner's Podium:** A high-visibility "King of the Hill" section using `Rich Panels` to highlight the top performers.

---

## 📊 Output Example

| Model | Prompt (t/s) | Gen (t/s) | BPW | Time (s) |
| --- | --- | --- | --- | --- |
| **Qwen3.5-2B-Q5_K_S.gguf** | 10.20 | 6.50 | 5.84 | 48.4s |
| **Qwen3.5-2B-Q5_K_M.gguf** | 10.00 | 6.20 | 6.05 | 53.1s |

---

## 🤝 Contributing

Feel free to fork this repo and add new features! Some ideas:

* Add VRAM detection for GPU offloading (`-ngl`).
* Create a graph using `matplotlib` from the generated CSV.

**Happy Benchmarking!** 🏆

---



```

This prevents you from accidentally trying to upload multi-gigabyte model files to your code repository!

Would you like me to help you write the `.gitignore` or a `requirements.txt` file as well?
