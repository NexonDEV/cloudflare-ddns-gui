import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import os
import json
import threading
import time
import subprocess
from scripts.config import load_config, save_config

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cloudflare DDNS Configurator")
        self.geometry("800x650")

        self.config_data = load_config()
        self.service_name = "cloudflare-ddns.service"

        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        service_frame = ttk.LabelFrame(main_container, text="Service Control")
        service_frame.pack(fill=tk.X, pady=5)
        self.create_service_widgets(service_frame)

        config_frame = ttk.LabelFrame(main_container, text="Configuration")
        config_frame.pack(fill=tk.X, pady=5)
        self.create_config_widgets(config_frame)

        log_frame = ttk.LabelFrame(main_container, text="Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_viewer = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_viewer.pack(fill=tk.BOTH, expand=True)

        self.log_thread = threading.Thread(target=self.update_logs, daemon=True)
        self.log_thread.start()

        self.status_thread = threading.Thread(target=self.update_status, daemon=True)
        self.status_thread.start()

    def create_service_widgets(self, parent):
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_canvas = tk.Canvas(control_frame, width=20, height=20)
        self.status_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self.status_indicator = self.status_canvas.create_oval(2, 2, 18, 18, fill="red")

        self.start_button = ttk.Button(control_frame, text="Start", command=lambda: self.run_systemctl("start"))
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=lambda: self.run_systemctl("stop"))
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def create_config_widgets(self, parent):
        self.config_text = tk.Text(parent, height=15)
        self.config_text.pack(fill=tk.X, padx=5, pady=5)
        self.config_text.insert(tk.END, json.dumps(self.config_data, indent=4))

        save_button = ttk.Button(parent, text="Save and Restart Service", command=self.save_and_restart)
        save_button.pack(pady=5)

    def run_systemctl(self, command):
        try:
            subprocess.run(["systemctl", command, self.service_name], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            if "permission" in e.stderr.decode().lower() or "authentication" in e.stderr.decode().lower():
                password = simpledialog.askstring("Sudo Password", "Enter your password:", show='*')
                if password:
                    sudo_command = f"echo {password} | sudo -S systemctl {command} {self.service_name}"
                    subprocess.run(sudo_command, shell=True, check=True, capture_output=True)
            else:
                messagebox.showerror("Error", f"Failed to run systemctl {command}: {e.stderr.decode()}")


    def save_and_restart(self):
        self.save_config_ui()
        self.run_systemctl("restart")


    def save_config_ui(self):
        try:
            new_config_str = self.config_text.get("1.0", tk.END)
            new_config = json.loads(new_config_str)
            save_config(new_config)
            self.config_data = new_config
            messagebox.showinfo("Success", "Configuration saved successfully.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON format.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def update_logs(self):
        log_file = os.path.join(os.getcwd(), '..', 'logs', 'ddns.log')
        if not os.path.exists(log_file):
           with open(log_file, 'w') as f:
                pass
        while True:
            try:
                with open(log_file, 'r') as f:
                    logs = f.read()
                    if self.log_viewer.get("1.0", tk.END).strip() != logs.strip():
                        self.log_viewer.delete("1.0", tk.END)
                        self.log_viewer.insert(tk.END, logs)
                        self.log_viewer.see(tk.END)
            except Exception as e:
                self.log_viewer.delete("1.0", tk.END)
                self.log_viewer.insert(tk.END, f"Error reading log file: {e}")
            time.sleep(1)

    def update_status(self):
        while True:
            try:
                result = subprocess.run(["systemctl", "is-active", self.service_name], capture_output=True, text=True)
                is_active = result.stdout.strip() == "active"

                if "failed" in result.stdout.strip().lower(): # Could be permission denied
                     password = simpledialog.askstring("Sudo Password", "Enter your password:", show='*')
                     if password:
                        sudo_command = f"echo {password} | sudo -S systemctl is-active {self.service_name}"
                        result = subprocess.run(sudo_command, shell=True, capture_output=True, text=True)
                        is_active = result.stdout.strip() == "active"

                if is_active:
                    self.status_canvas.itemconfig(self.status_indicator, fill="green")
                else:
                    self.status_canvas.itemconfig(self.status_indicator, fill="red")
            except Exception:
                self.status_canvas.itemconfig(self.status_indicator, fill="red")
            time.sleep(5)


if __name__ == "__main__":
    if os.geteuid() != 0:
        password = simpledialog.askstring("Sudo Password", "Enter your password to run the application:", show='*')
        if password:
            command = f"echo {password} | sudo -S python3 " + " ".join(sys.argv)
            os.system(command)
            sys.exit()
        else:
            sys.exit("Sudo password required.")

    app = App()
    app.mainloop()
