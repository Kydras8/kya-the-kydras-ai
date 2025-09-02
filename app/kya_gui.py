#!/usr/bin/env python3
import os, sys, sqlite3, subprocess, time, json
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

INSTALL_DIR = "/opt/kydras-sysagent"
DB_PATH = "/var/lib/kydras-sysagent/agent.db"
CONF_PATH = "/etc/kydras-sysagent.conf"
KYA = "/usr/local/bin/kya"

PROFILES = {
    "Red-Team": {
        "DISABLE_CHECKS": "unattended_upgrades",
        "AUTO_APPLY": "",
        "SAMPLE_SECONDS": "30",
        "LOW_RAM_MB": "300",
        "DISK_FULL_PCT": "90",
        "JOURNAL_MAX_MB": "300",
        "APT_CACHE_MAX_MB": "1024",
        "SWAPPINESS_HIGH_GT": "80",
    },
    "Build": {
        "DISABLE_CHECKS": "",
        "AUTO_APPLY": "apt_cache,journald_size",
        "SAMPLE_SECONDS": "60",
        "LOW_RAM_MB": "500",
        "DISK_FULL_PCT": "85",
        "JOURNAL_MAX_MB": "700",
        "APT_CACHE_MAX_MB": "700",
        "SWAPPINESS_HIGH_GT": "60",
    },
    "Headless": {
        "DISABLE_CHECKS": "",
        "AUTO_APPLY": "apt_cache,journald_size",
        "SAMPLE_SECONDS": "120",
        "LOW_RAM_MB": "400",
        "DISK_FULL_PCT": "90",
        "JOURNAL_MAX_MB": "500",
        "APT_CACHE_MAX_MB": "600",
        "SWAPPINESS_HIGH_GT": "60",
    },
    "Custom": {}
}

def db_conn(): return sqlite3.connect(DB_PATH)

def fetch_suggestions():
    try:
        conn = db_conn()
        cur = conn.execute("SELECT id, ts, check_name, severity, message, fix_cmd FROM suggestions WHERE status='open' ORDER BY id DESC")
        rows = cur.fetchall(); conn.close(); return rows, None
    except Exception as e:
        return [], str(e)

def fetch_last_sample():
    try:
        conn = db_conn()
        cur = conn.execute("SELECT ts,cpu,mem_used,mem_total,load1,load5,load15 FROM metrics ORDER BY ts DESC LIMIT 1")
        row = cur.fetchone(); conn.close(); return row, None
    except Exception as e:
        return None, str(e)

def read_conf():
    data = {}
    try:
        with open(CONF_PATH) as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln: continue
                k,v = ln.split("=",1); data[k.strip().upper()] = v.strip()
    except Exception:
        pass
    return data

def write_conf_from_profile(name):
    prof = PROFILES.get(name, {})
    cur = read_conf() if name == "Custom" else {}
    cur["PROFILE"] = name
    for k,v in prof.items():
        cur[k] = v
    defaults = {
        "DISABLE_CHECKS":"", "AUTO_APPLY":"", "SAMPLE_SECONDS":"60",
        "LOW_RAM_MB":"500","DISK_FULL_PCT":"85","JOURNAL_MAX_MB":"1024",
        "APT_CACHE_MAX_MB":"500","SWAPPINESS_HIGH_GT":"60"
    }
    for k, dv in defaults.items():
        cur.setdefault(k, dv)
    content = "\n".join(f"{k}={cur[k]}" for k in ["PROFILE","DISABLE_CHECKS","AUTO_APPLY","SAMPLE_SECONDS",
                                                  "LOW_RAM_MB","DISK_FULL_PCT","JOURNAL_MAX_MB",
                                                  "APT_CACHE_MAX_MB","SWAPPINESS_HIGH_GT"]) + "\n"
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        with open(CONF_PATH,"w") as f: f.write(content)
        return True, ""
    p = subprocess.run(["sudo","tee",CONF_PATH], input=content, text=True, capture_output=True)
    return (p.returncode==0, p.stderr)

def restart_agent():
    if hasattr(os,"geteuid") and os.geteuid()==0:
        return subprocess.run(["systemctl","restart","kydras-sysagent"]).returncode==0
    return subprocess.run(["pkexec","systemctl","restart","kydras-sysagent"]).returncode==0

def du_bytes(path):
    try:
        out = subprocess.check_output(["du","-sb",path], text=True).split()[0]; return int(out)
    except Exception:
        return 0

def bytes_h(n):
    units=["B","KB","MB","GB","TB"]; i=0; f=float(n)
    while f>=1024 and i<4: f/=1024; i+=1
    return f"{f:.1f}{units[i]}"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kydras System Agent — Control Center")
        self.geometry("1150x640")
        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True)
        self.build_tab_suggestions()
        self.build_tab_doctor()
        self.build_tab_profiles()
        self.refresh_all()

    # ---------- Suggestions ----------
    def build_tab_suggestions(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="Suggestions")
        self.status_var = tk.StringVar(value="Loading…")
        hdr = ttk.Frame(tab); hdr.pack(fill="x", padx=8, pady=6)
        ttk.Label(hdr, textvariable=self.status_var).pack(side="left")
        ttk.Button(hdr, text="Refresh", command=self.refresh_all).pack(side="right")
        cols = ("id","when","check","severity","message","fix")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings", height=16)
        for c,w in [("id",60),("when",160),("check",160),("severity",90),("message",500),("fix",150)]:
            self.tree.heading(c, text=c.upper()); self.tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=4)
        vsb.pack(side="left", fill="y", padx=(0,8), pady=4)
        btns = ttk.Frame(tab); btns.pack(fill="x", padx=8, pady=6)
        ttk.Button(btns, text="Apply", command=self.apply_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Dismiss", command=self.dismiss_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Tune…", command=self.run_tune).pack(side="left", padx=4)
        ttk.Button(btns, text="Tail Logs", command=self.tail_logs).pack(side="left", padx=4)
        ttk.Button(btns, text="Open Tray", command=self.open_tray).pack(side="left", padx=4)
        self.out = tk.Text(tab, height=8); self.out.pack(fill="both", expand=False, padx=8, pady=(0,8))

    def log(self, msg): self.out.insert("end", msg + "\n"); self.out.see("end")

    def refresh_all(self):
        last, err = fetch_last_sample()
        if last:
            ts, cpu, mu, mt, l1, l5, l15 = last
            when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            self.status_var.set(f"Last sample: {when}  CPU: {cpu:.1f}%  Mem: {mu/mt*100:.1f}%  Load: {l1:.2f}/{l5:.2f}/{l15:.2f}")
        else:
            self.status_var.set(f"No metrics yet ({err})" if err else "No metrics yet")
        for x in self.tree.get_children(): self.tree.delete(x)
        rows, err = fetch_suggestions()
        if err: self.log(f"[error] DB read failed: {err}. If not using group access, run as root: sudo kya-gui")
        for sid, ts, chk, sev, msg, fix in rows:
            when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
            self.tree.insert("", "end", iid=str(sid), values=(sid, when, chk, sev, msg, fix or ""))

    def selected_id(self):
        sel = self.tree.selection()
        if not sel: messagebox.showinfo("Kydras", "Select a suggestion first."); return None
        return int(sel[0])

    def _rooted(self): return hasattr(os,"geteuid") and os.geteuid()==0
    def _term(self): return os.environ.get("TERMINAL") or "x-terminal-emulator"

    def apply_selected(self):
        sid = self.selected_id()
        if not sid: return
        self.log(f"Applying suggestion {sid} …")
        if self._rooted():
            r = subprocess.run([KYA,"apply",str(sid),"--yes"], text=True, capture_output=True)
            if r.returncode==0: self.log(f"[ok] Applied {sid}"); self.refresh_all()
            else: self.log(f"[ERR] Apply exit {r.returncode}\n{r.stderr}")
        else:
            try: subprocess.Popen([self._term(), "-e", "bash", "-lc", f"sudo {KYA} apply {sid}"])
            except Exception: self.log(f"Run in a terminal: sudo {KYA} apply {sid}")

    def dismiss_selected(self):
        sid = self.selected_id()
        if not sid: return
        if self._rooted():
            r = subprocess.run([KYA,"dismiss",str(sid)], text=True, capture_output=True)
            if r.returncode==0: self.log(f"[ok] Dismissed {sid}"); self.refresh_all()
            else: self.log(f"[ERR] Dismiss exit {r.returncode}\n{r.stderr}")
        else:
            try: subprocess.Popen([self._term(), "-e", "bash", "-lc", f"sudo {KYA} dismiss {sid}"])
            except Exception: self.log(f"Run in a terminal: sudo {KYA} dismiss {sid}")

    def run_tune(self):
        try: subprocess.Popen([self._term(), "-e", "bash", "-lc", f"sudo {KYA} tune"])
        except Exception: self.log("Run: sudo kya tune")

    def tail_logs(self):
        try: subprocess.Popen([self._term(), "-e", "bash", "-lc", "sudo journalctl -u kydras-sysagent -f"])
        except Exception:
            out = subprocess.run(["sudo","journalctl","-u","kydras-sysagent","-n","100"], text=True, capture_output=True)
            self.out.delete("1.0","end"); self.out.insert("end", out.stdout or out.stderr)

    def open_tray(self):
        try: subprocess.Popen(["kya-tray"])
        except Exception: self.log("kya-tray not found or failed to launch")

    # ---------- Doctor ----------
    def build_tab_doctor(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="Doctor")
        frame = ttk.Frame(tab); frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.doc_text = tk.Text(frame, height=18); self.doc_text.pack(fill="both", expand=True)
        btns = ttk.Frame(tab); btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Run Doctor", command=self.run_doctor).pack(side="left", padx=4)
        ttk.Button(btns, text="Fix: Set swappiness=10", command=lambda: self.run_fix("echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-kydras.conf && sudo sysctl -w vm.swappiness=10")).pack(side="left", padx=4)
        ttk.Button(btns, text="Fix: Enable ZRAM", command=lambda: self.run_fix("sudo apt -y install zram-tools && echo ALGO=lz4 | sudo tee /etc/default/zramswap >/dev/null && sudo systemctl enable --now zramswap.service")).pack(side="left", padx=4)
        ttk.Button(btns, text="Fix: Vacuum journals", command=lambda: self.run_fix("sudo journalctl --vacuum-time=14d")).pack(side="left", padx=4)
        ttk.Button(btns, text="Fix: Clean apt cache", command=lambda: self.run_fix("sudo apt clean && sudo apt autoclean || true")).pack(side="left", padx=4)

    def run_doctor(self):
        vm = psutil.virtual_memory(); du = psutil.disk_usage("/")
        l1,l5,l15 = os.getloadavg()
        swp = open("/proc/sys/vm/swappiness").read().strip()
        zram = subprocess.run(["systemctl","is-active","zramswap.service"], text=True, capture_output=True)
        apt_sz = du_bytes("/var/cache/apt")
        j_sz = du_bytes("/var/log/journal") if os.path.isdir("/var/log/journal") else 0
        lines = []
        lines.append(f"CPU load: {l1:.2f}/{l5:.2f}/{l15:.2f}")
        lines.append(f"Memory: {vm.percent:.1f}% used  ({bytes_h(vm.used)} / {bytes_h(vm.total)})")
        lines.append(f"Disk /: {du.percent:.1f}% used  ({bytes_h(du.used)} / {bytes_h(du.total)})")
        lines.append(f"Swappiness: {swp}")
        lines.append(f"ZRAM: {'active' if zram.stdout.strip()=='active' else 'inactive'}")
        lines.append(f"APT cache: {bytes_h(apt_sz)}")
        lines.append(f"journald size: {bytes_h(j_sz)}")
        self.doc_text.delete("1.0","end"); self.doc_text.insert("end","\n".join(lines) + "\n")

    def run_fix(self, cmd):
        term = self._term()
        try: subprocess.Popen([term, "-e", "bash", "-lc", cmd])
        except Exception: messagebox.showinfo("Kydras", f"Run this in a terminal:\n{cmd}")

    # ---------- Profiles ----------
    def build_tab_profiles(self):
        tab = ttk.Frame(self.nb); self.nb.add(tab, text="Profiles")
        cur = read_conf()
        cur_name = cur.get("PROFILE","Custom")
        top = ttk.Frame(tab); top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Current Profile:").pack(side="left")
        self.prof_var = tk.StringVar(value=cur_name if cur_name in PROFILES else "Custom")
        self.prof_sel = ttk.Combobox(top, textvariable=self.prof_var, values=list(PROFILES.keys()), state="readonly", width=20)
        self.prof_sel.pack(side="left", padx=8)
        desc = {
            "Red-Team":"No auto updates; tighter RAM/disk thresholds; faster sampling; minimal noise.",
            "Build":"Auto-apply log/cache cleanup; balanced thresholds; standard sampling.",
            "Headless":"Longer sampling; safe auto-apply cleanup; conservative thresholds.",
            "Custom":"Use your exact /etc/kydras-sysagent.conf values."
        }
        self.prof_desc = tk.StringVar(value=desc.get(self.prof_var.get(),""))
        ttk.Label(tab, textvariable=self.prof_desc).pack(anchor="w", padx=8)
        btns = ttk.Frame(tab); btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Apply Profile", command=self.apply_profile).pack(side="left", padx=4)
        ttk.Button(btns, text="Open Config", command=self.open_conf).pack(side="left", padx=4)
        ttk.Button(btns, text="Restart Agent", command=lambda: restart_agent() or None).pack(side="left", padx=4)
        self.conf_view = tk.Text(tab, height=16)
        self.conf_view.pack(fill="both", expand=True, padx=8, pady=(0,8))
        self.reload_conf_view()
        def on_change(*_): self.prof_desc.set(desc.get(self.prof_var.get(),""))
        self.prof_var.trace_add("write", on_change)

    def reload_conf_view(self):
        c = ""
        try: c = open(CONF_PATH).read()
        except Exception: c = "(config not found or no permission)"
        self.conf_view.delete("1.0","end"); self.conf_view.insert("end", c)

    def apply_profile(self):
        name = self.prof_var.get()
        ok, err = write_conf_from_profile(name)
        if not ok:
            messagebox.showerror("Kydras", f"Failed to write config:\n{err}"); return
        if restart_agent():
            messagebox.showinfo("Kydras", f"Profile '{name}' applied and agent restarted.")
        else:
            messagebox.showwarning("Kydras", "Config written. Failed to restart agent; try manually.")
        self.reload_conf_view()

    def open_conf(self):
        term = self._term()
        try:
            subprocess.Popen([term,"-e","bash","-lc", f"sudo sensible-editor {CONF_PATH} || sudo nano {CONF_PATH}"])
        except Exception:
            messagebox.showinfo("Kydras", f"Edit as root: {CONF_PATH}")

if __name__ == "__main__":
    sys.path.insert(0, INSTALL_DIR)
    App().mainloop()
