import subprocess
import time
import os
import re
import json
import csv
import argparse
import sys
import psutil

# Try to import rich components
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Fixed prompt
PROMPT = "explain in simple terms the difference between CPU and GPU during inference"

# Regex patterns
SIMPLE_PROMPT_RE = re.compile(r"Prompt:\s*([\d.]+)\s*t/s")
SIMPLE_GEN_RE = re.compile(r"Generation:\s*([\d.]+)\s*t/s")
PROMPT_SPEED_RE = re.compile(r"prompt eval time =.*?(\d+\.\d+)\s*tokens per second")
GENERATION_SPEED_RE = re.compile(r"eval time =.*?(\d+\.\d+)\s*tokens per second")
BPW_RE = re.compile(r"file size\s*=\s*[\d.]+ GiB\s*\(\s*([\d.]+)\s*BPW\)")

def get_system_info():
    ram = psutil.virtual_memory()
    available_gb = ram.available / (1024 ** 3)
    max_threads = psutil.cpu_count(logical=True)
    return round(available_gb, 2), max_threads

def extract_speeds_and_bpw(output, error):
    prompt_speed = gen_speed = bpw = None
    
    prompt_match = SIMPLE_PROMPT_RE.search(output)
    if prompt_match: prompt_speed = float(prompt_match.group(1))
    
    gen_match = SIMPLE_GEN_RE.search(output)
    if gen_match: gen_speed = float(gen_match.group(1))

    if prompt_speed is None:
        detailed_prompt = PROMPT_SPEED_RE.search(output)
        if detailed_prompt: prompt_speed = float(detailed_prompt.group(1))

    if gen_speed is None:
        detailed_gen = GENERATION_SPEED_RE.search(output)
        if detailed_gen: gen_speed = float(detailed_gen.group(1))

    bpw_match = BPW_RE.search(error)
    if bpw_match: bpw = float(bpw_match.group(1))

    return {"prompt_speed_tps": prompt_speed, "generation_speed_tps": gen_speed, "bpw": bpw}

def execute_benchmark(folder_path, model_file, thread_count, log_file):
    model_path = os.path.join(folder_path, model_file)
    command = [
        r".\llama-cli.exe", "-m", model_path, "-ngl", "0", "-t", str(thread_count),
        "--mmap", "-n", "200", "-st", "-p", PROMPT, "-lv", "3",
        "--reasoning-budget", "0", "--log-file", log_file
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
        metrics = extract_speeds_and_bpw(result.stdout, result.stderr)
        return {
            "model": model_file, "prompt_speed_tps": metrics["prompt_speed_tps"],
            "generation_speed_tps": metrics["generation_speed_tps"], "bpw": metrics["bpw"],
            "output": result.stdout, "error": result.stderr, "returncode": result.returncode
        }
    except Exception as e:
        return {
            "model": model_file, "prompt_speed_tps": None, "generation_speed_tps": None,
            "bpw": None, "error": str(e), "returncode": None
        }

def run_model_in_folder(folder_path, thread_count, log_file="mylog.txt"):
    models = [f for f in os.listdir(folder_path) if f.endswith(".gguf")]
    results = []

    if HAS_RICH:
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=Console()
        )
        
        with progress:
            task = progress.add_task("[cyan]Benchmarking...", total=len(models))
            for model_file in models:
                progress.update(task, description=f"🔍 Testing: [bold yellow]{model_file}[/bold yellow]")
                start_time = time.time()
                res = execute_benchmark(folder_path, model_file, thread_count, log_file)
                res["total_duration_sec"] = round(time.time() - start_time, 2)
                results.append(res)
                progress.advance(task)
    else:
        for model_file in models:
            start_time = time.time()
            res = execute_benchmark(folder_path, model_file, thread_count, log_file)
            res["total_duration_sec"] = round(time.time() - start_time, 2)
            results.append(res)
            
    return results

from rich.table import Table # Ensure Table is imported at the top

def print_winners(results):
    """Identifies and displays the top performing models with corrected alignment and formatting."""
    if not results or not HAS_RICH:
        return

    # Filter out N/A values for comparison
    valid_prompt = [r for r in results if r.get("prompt_speed_tps") is not None]
    valid_gen = [r for r in results if r.get("generation_speed_tps") is not None]

    best_p = max(valid_prompt, key=lambda x: x["prompt_speed_tps"]) if valid_prompt else None
    best_g = max(valid_gen, key=lambda x: x["generation_speed_tps"]) if valid_gen else None

    console = Console()

    # 1. Create a grid for the two winner panels
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1) # Left side 50%
    grid.add_column(ratio=1) # Right side 50%

    # 2. Build the Prompt Winner Panel
    p_panel = ""
    if best_p:
        p_text = Text.assemble(
            ("Prompt King\n", "bold cyan"), 
            (best_p['model'], "yellow"), 
            f"\n{best_p['prompt_speed_tps']} t/s"
        )
        p_text.justify = "center" # This is where justify belongs
        p_panel = Panel(p_text, title="🚀 Fastest Load", border_style="cyan", expand=True)

    # 3. Build the Generation Winner Panel
    g_panel = ""
    if best_g:
        g_text = Text.assemble(
            ("Generation King\n", "bold green"), 
            (best_g['model'], "yellow"), 
            f"\n{best_g['generation_speed_tps']} t/s"
        )
        g_text.justify = "center"
        g_panel = Panel(g_text, title="✍️ Fastest Gen", border_style="green", expand=True)

    grid.add_row(p_panel, g_panel)

    # 4. Final Print
    console.print("\n")
    # Fixed: Removed justify from Panel and used a Text object instead
    title_text = Text("🏆 BENCHMARK WINNERS", style="bold gold1", justify="center")
    console.print(Panel(title_text, border_style="gold1", expand=False))
    
    console.print(grid)

def generate_markdown_table(results):
    sorted_results = sorted(results, key=lambda x: x["prompt_speed_tps"] if x["prompt_speed_tps"] is not None else 0.0, reverse=True)
    md = "# 📊 Benchmark Summary Table\n\n| Model | Prompt (t/s) | Gen (t/s) | BPW | Time (s) |\n| :--- | :---: | :---: | :---: | :---: |\n"
    for r in sorted_results:
        p = f"{r['prompt_speed_tps']:.2f}" if r["prompt_speed_tps"] else "N/A"
        g = f"{r['generation_speed_tps']:.2f}" if r["generation_speed_tps"] else "N/A"
        b = f"{r['bpw']:.2f}" if r["bpw"] else "N/A"
        t = f"{r['total_duration_sec']:.1f}s" if "total_duration_sec" in r else "N/A"
        md += f"| **{r['model']}** | {p} | {g} | {b} | {t} |\n"
    return md

def save_results_to_files(results, base_filename):
    with open(f"{base_filename}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(f"{base_filename}.md", "w", encoding="utf-8") as f:
        f.write(generate_markdown_table(results))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark GGUF models")
    parser.add_argument("--folder", default=".\\models")
    parser.add_argument("--output", default="benchmark_results")
    args = parser.parse_args()

    if not os.path.exists(args.folder):
        print(f"❌ Folder not found: {args.folder}")
        sys.exit(1)

    avail_ram, max_threads = get_system_info()
    optimal_threads = max(1, max_threads - 1)
    models = [f for f in os.listdir(args.folder) if f.endswith(".gguf")]
    
    print("\n" + "="*50 + "\n📋 BENCHMARK PRE-FLIGHT CHECK\n" + "="*50)
    print(f"🖥️  System RAM Available: {avail_ram} GB\n🧬 CPU Threads (Total):  {max_threads}\n⚙️  Threads for Testing: {optimal_threads} (Max-1)")
    print(f"📂 Model Folder:         {args.folder}\n📦 Models Found ({len(models)}):")
    for m in models: print(f"   - {m}")
    print("="*50)
    
    if input("\nProceed with benchmarking? (y/n): ").strip().lower() == 'y':
        results = run_model_in_folder(args.folder, optimal_threads)
        save_results_to_files(results, args.output)
        
        if HAS_RICH:
            Console().print("\n", Markdown(generate_markdown_table(results)))
            print_winners(results)
        else:
            print(generate_markdown_table(results))
    else:
        print("🛑 Benchmarking cancelled.")