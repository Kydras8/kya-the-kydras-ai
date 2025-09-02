#!/usr/bin/env python3
import os, sys, sqlite3, time, json, subprocess, threading
from pathlib import Path

DB_PATH = "/var/lib/kydras-sysagent/agent.db"
KYA = "/usr/local/bin/kya"

STATE_DIR = Path(os.path.expanduser("~/.local/share/kydras-sysagent"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "tray_state.json"

# ---- GI / AppIndicator detection (version-pinned) ----
HAVE_GI = False
HAVE_INDICATOR = False
try:
    import gi
    gi.require_version("Notify", "0.7")
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Notify, Gtk
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as AppIndicator
        HAVE_INDICATOR = True
    except Exception:
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AppIndicator
            HAVE_INDICATOR = True
        except Exception:
            pass
    HAVE_GI = True
except Exception:
    pass

# ---- Helpers ----
def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_id": 0}

def save_state(st):
    STATE_FILE.write_text(json.dumps(st))

def db_conn():
    return sqlite3.connect(DB_PATH)

def newest_open():
    try:
        conn = db_conn()
        cur = conn.execute("SELECT max(id) FROM suggestions WHERE status='open'")
        row = cur.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0

def fetch_new_suggestions(since_id):
    try:
        conn = db_conn()
        cur = conn.execute("""
            SELECT id, ts, check_name, severity, message
            FROM suggestions
            WHERE status='open' AND id > ?
            ORDER BY id ASC
        """, (since_id,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

def open_terminal(cmd):
    term = os.environ.get("TERMINAL") or "x-terminal-emulator"
    try:
        subprocess.Popen([term, "-e", "bash", "-lc", cmd])
    except Exception:
        pass

def apply_id(sid):
    # Root → apply directly
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        subprocess.Popen([KYA, "apply", str(sid), "--yes"] )
        return
    # Try pkexec (GUI auth)
    try:
        subprocess.Popen(["pkexec", KYA, "apply", str(sid), "--yes"])
        return
    except Exception:
        pass
    # Fallback: open terminal for sudo prompt
    open_terminal(f"sudo {KYA} apply {sid}")

def dismiss_id(sid):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        subprocess.Popen([KYA, "dismiss", str(sid)])
        return
    try:
        subprocess.Popen(["pkexec", KYA, "dismiss", str(sid)])
        return
    except Exception:
        pass
    open_terminal(f"sudo {KYA} dismiss {sid}")

# ---- Notification + tray ----
def notify_for(row):
    sid, ts, chk, sev, msg = row
    title = f"Kydras: new suggestion #{sid}"
    body = f"[{sev}] {chk}\n{msg}"

    if HAVE_GI:
        try:
            Notify.init("Kydras System Agent")
            n = Notify.Notification.new(title, body, "dialog-information")
            try:
                n.add_action("apply", "Apply", lambda n,a: apply_id(sid))
                n.add_action("dismiss", "Dismiss", lambda n,a: dismiss_id(sid))
                n.add_action("open", "Open GUI", lambda n,a: subprocess.Popen(["kya-gui"]))
            except Exception:
                pass
            n.show()
            return
        except Exception:
            pass

    # Fallback: libnotify-bin
    try:
        subprocess.Popen(["notify-send", title, body])
    except Exception:
        pass

def poll_loop():
    st = load_state()
    last = st.get("last_id", 0)
    # Seed to current max so we don't spam on first run
    if last == 0:
        last = newest_open()
        save_state({"last_id": last})
    while True:
        rows = fetch_new_suggestions(last)
        for row in rows:
            last = max(last, row[0])
            notify_for(row)
            save_state({"last_id": last})
        time.sleep(20)

class TrayApp:
    def __init__(self):
        if HAVE_GI:
            Notify.init("Kydras System Agent")
        if HAVE_INDICATOR:
            self.ind = AppIndicator.Indicator.new(
                "kydras-sysagent", "utilities-system-monitor",
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )
            self.ind.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.ind.set_menu(self.build_menu())
        threading.Thread(target=poll_loop, daemon=True).start()

    def build_menu(self):
        menu = Gtk.Menu()
        def add(label, cb):
            item = Gtk.MenuItem(label=label)
            item.connect("activate", cb)
            item.show()
            menu.append(item)
        add("Open GUI", lambda *_: subprocess.Popen(["kya-gui"]))
        add("Status",   lambda *_: open_terminal(f"{KYA} status; echo; read -p 'Press Enter to close'"))
        add("Quit",     lambda *_: Gtk.main_quit())
        return menu

def main():
    if HAVE_GI:
        app = TrayApp()
        try:
            Gtk.main()
        except NameError:
            GLib.MainLoop().run()
    else:
        # No GI: just notify in the background every 20s
        poll_loop()

if __name__ == "__main__":
    main()
