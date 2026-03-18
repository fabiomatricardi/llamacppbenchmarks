import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os

class GemmaGui:
    def __init__(self, root):
        self.root = root
        self.root.title("GGUF Runner")
        self.process = None

        # --- Model File Selection ---
        tk.Label(root, text="Model File (GGUF):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.model_path = tk.StringVar()
        tk.Entry(root, textvariable=self.model_path, width=50).grid(row=0, column=1, padx=5)
        tk.Button(root, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5)

        # --- Numeric Parameters ---
        # GPU Layers (-ngl)
        tk.Label(root, text="GPU Layers (-ngl):").grid(row=1, column=0, sticky="w", padx=5)
        self.ngl = tk.IntVar(value=0)
        tk.Spinbox(root, from_=0, to=999, textvariable=self.ngl).grid(row=1, column=1, sticky="w", padx=5)

        # Threads (-t)
        tk.Label(root, text="Threads (-t):").grid(row=2, column=0, sticky="w", padx=5)
        self.threads = tk.IntVar(value=3)
        tk.Spinbox(root, from_=1, to=9, textvariable=self.threads).grid(row=2, column=1, sticky="w", padx=5)

        # Context Size (-c)
        tk.Label(root, text="Context Size (-c):").grid(row=3, column=0, sticky="w", padx=5)
        self.context = tk.IntVar(value=4096)
        tk.Spinbox(root, from_=2048, to=32768, textvariable=self.context).grid(row=3, column=1, sticky="w", padx=5)

        # --- Checkbox Options ---
        self.ctk_var = tk.BooleanVar()
        tk.Checkbutton(root, text="Quantize K Cache (Q8_0)", variable=self.ctk_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=5)

        self.ctv_var = tk.BooleanVar()
        tk.Checkbutton(root, text="Quantize V Cache (Q8_0)", variable=self.ctv_var).grid(row=5, column=0, columnspan=2, sticky="w", padx=5)

        self.fa_var = tk.BooleanVar()
        tk.Checkbutton(root, text="Flash Attention (-fa)", variable=self.fa_var).grid(row=6, column=0, columnspan=2, sticky="w", padx=5)

        # --- Execution & Monitoring ---
        self.run_btn = tk.Button(root, text="Run Inference", command=self.run_inference, bg="green", fg="white")
        self.run_btn.grid(row=7, column=0, pady=10)

        self.status_label = tk.Label(root, text="PID: None", fg="blue")
        self.status_label.grid(row=7, column=1, sticky="w")

        # Output Text Box
        self.output_text = tk.Text(root, height=15, width=70)
        self.output_text.grid(row=8, column=0, columnspan=3, padx=10, pady=10)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("GGUF files", "*.gguf")])
        if filename:
            self.model_path.set(filename)

    def run_inference(self):
        if not self.model_path.get():
            messagebox.showerror("Error", "Please select a model file first.")
            return

        # Construct Command
        command = [
            '.\\llama-cli.exe',
            '-m', self.model_path.get(),
            '-ngl', str(self.ngl.get()),
            '-t', str(self.threads.get()),
            '--mmap',
            '-n', '200',
            '-p', 'explain in simple terms the difference between CPU and GPU during inference',
            '-c', str(self.context.get()),
            '--log-file', 'mylog.txt'
        ]

        if self.ctk_var.get(): command.extend(['-ctk', 'q8_0'])
        if self.ctv_var.get(): command.extend(['-ctv', 'q8_0'])
        if self.fa_var.get(): command.extend(['-fa', 'on'])

        # Clear output and start thread
        self.output_text.delete(1.0, tk.END)
        threading.Thread(target=self.execute_command, args=(command,), daemon=True).start()

    def execute_command(self, command):
        try:
            # Start process
            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, # Merge stderr into stdout for easier reading
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            self.status_label.config(text=f"PID: {self.process.pid}")
            
            # Read output stream
            for line in iter(self.process.stdout.readline, ''):
                self.output_text.insert(tk.END, line)
                self.output_text.see(tk.END)
            
            self.process.stdout.close()
            return_code = self.process.wait()
            self.output_text.insert(tk.END, f"\n--- Process finished with code {return_code} ---")
            
        except Exception as e:
            messagebox.showerror("Execution Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = GemmaGui(root)
    root.mainloop()