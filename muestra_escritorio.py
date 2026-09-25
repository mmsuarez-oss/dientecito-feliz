"""Dientecito Feliz - Clinica Odontologica UAM (muestra)
Pacientes, citas y odontograma interactivo. Tkinter + SQLite.
"""
import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

DB = Path(__file__).with_name("dientecito.db")

ESTADOS = {  # estado: color
    "Sano": "#ffffff",
    "Caries": "#e74c3c",
    "Obturado": "#3498db",
    "Corona": "#f1c40f",
    "Extraido": "#7f8c8d",
}
# Numeracion FDI: arcada superior e inferior, de derecha a izquierda del paciente
SUPERIOR = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
INFERIOR = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]


def conectar():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS pacientes(
            id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, cedula TEXT UNIQUE NOT NULL,
            telefono TEXT, nacimiento TEXT, alergias TEXT);
        CREATE TABLE IF NOT EXISTS citas(
            id INTEGER PRIMARY KEY,
            paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
            fecha TEXT NOT NULL, hora TEXT NOT NULL, motivo TEXT, estudiante TEXT);
        CREATE TABLE IF NOT EXISTS odontograma(
            paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
            diente INTEGER, estado TEXT, PRIMARY KEY(paciente_id, diente));
    """)
    return con


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dientecito Feliz - Clinica Odontologica UAM")
        self.geometry("900x560")
        self.con = conectar()

        ttk.Style(self).configure("Treeview", rowheight=24)
        tk.Label(self, text="🦷 Dientecito Feliz", font=("Segoe UI", 18, "bold"),
                 fg="#1b6ca8").pack(pady=(10, 0))

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tab_pacientes(tabs)
        self.tab_citas(tabs)
        self.tab_odontograma(tabs)
        tabs.bind("<<NotebookTabChanged>>", lambda e: self.refrescar_combos())
        self.refrescar_pacientes()

    # ---------- utilidades ----------
    def formulario(self, padre, campos):
        vars_ = {}
        for i, campo in enumerate(campos):
            ttk.Label(padre, text=campo + ":").grid(row=i, column=0, sticky="w", pady=3)
            vars_[campo] = tk.StringVar()
            ttk.Entry(padre, textvariable=vars_[campo], width=28).grid(row=i, column=1, pady=3)
        return vars_

    def tabla(self, padre, columnas):
        t = ttk.Treeview(padre, columns=columnas, show="headings")
        for c in columnas:
            t.heading(c, text=c)
            t.column(c, width=110)
        t.pack(fill="both", expand=True)
        return t

    def pacientes(self):
        return self.con.execute("SELECT id, nombre, cedula FROM pacientes ORDER BY nombre").fetchall()

    def refrescar_combos(self):
        opciones = [f"{i} - {n} ({c})" for i, n, c in self.pacientes()]
        for combo in (self.cita_paciente, self.odo_paciente):
            combo["values"] = opciones

    @staticmethod
    def id_de(combo):
        return int(combo.get().split(" - ")[0]) if combo.get() else None

    # ---------- Pacientes ----------
    def tab_pacientes(self, tabs):
        f = ttk.Frame(tabs, padding=10)
        tabs.add(f, text="Pacientes")
        izq = ttk.LabelFrame(f, text="Nuevo paciente", padding=10)
        izq.pack(side="left", fill="y")
        self.pac = self.formulario(izq, ["Nombre", "Cedula", "Telefono", "Nacimiento", "Alergias"])
        ttk.Button(izq, text="Guardar", command=self.guardar_paciente).grid(row=5, column=1, sticky="e", pady=8)
        ttk.Button(izq, text="Eliminar seleccionado", command=self.eliminar_paciente).grid(row=6, column=1, sticky="e")

        der = ttk.Frame(f, padding=(10, 0))
        der.pack(side="left", fill="both", expand=True)
        self.t_pac = self.tabla(der, ("ID", "Nombre", "Cedula", "Telefono", "Nacimiento", "Alergias"))

    def guardar_paciente(self):
        v = {k: x.get().strip() for k, x in self.pac.items()}
        if not v["Nombre"] or not v["Cedula"]:
            return messagebox.showwarning("Faltan datos", "Nombre y cedula son obligatorios.")
        try:
            with self.con:
                self.con.execute("INSERT INTO pacientes(nombre, cedula, telefono, nacimiento, alergias) VALUES (?,?,?,?,?)",
                                 (v["Nombre"], v["Cedula"], v["Telefono"], v["Nacimiento"], v["Alergias"]))
        except sqlite3.IntegrityError:
            return messagebox.showerror("Duplicado", "Ya existe un paciente con esa cedula.")
        for x in self.pac.values():
            x.set("")
        self.refrescar_pacientes()

    def eliminar_paciente(self):
        sel = self.t_pac.selection()
        if sel and messagebox.askyesno("Eliminar", "¿Eliminar paciente con sus citas y odontograma?"):
            with self.con:
                self.con.execute("DELETE FROM pacientes WHERE id=?", (self.t_pac.item(sel[0])["values"][0],))
            self.refrescar_pacientes()

    def refrescar_pacientes(self):
        self.t_pac.delete(*self.t_pac.get_children())
        for fila in self.con.execute("SELECT * FROM pacientes ORDER BY nombre"):
            self.t_pac.insert("", "end", values=fila)
        self.refrescar_combos()
        self.refrescar_citas()

    # ---------- Citas ----------
    def tab_citas(self, tabs):
        f = ttk.Frame(tabs, padding=10)
        tabs.add(f, text="Citas")
        izq = ttk.LabelFrame(f, text="Agendar cita", padding=10)
        izq.pack(side="left", fill="y")
        ttk.Label(izq, text="Paciente:").grid(row=0, column=0, sticky="w")
        self.cita_paciente = ttk.Combobox(izq, state="readonly", width=26)
        self.cita_paciente.grid(row=0, column=1, pady=3)
        sub = ttk.Frame(izq)
        sub.grid(row=1, column=0, columnspan=2, sticky="w")
        self.cita = self.formulario(sub, ["Fecha (AAAA-MM-DD)", "Hora (HH:MM)", "Motivo", "Estudiante"])
        ttk.Button(izq, text="Agendar", command=self.guardar_cita).grid(row=2, column=1, sticky="e", pady=8)

        der = ttk.Frame(f, padding=(10, 0))
        der.pack(side="left", fill="both", expand=True)
        self.t_cit = self.tabla(der, ("Fecha", "Hora", "Paciente", "Motivo", "Estudiante"))

    def guardar_cita(self):
        pid = self.id_de(self.cita_paciente)
        v = [x.get().strip() for x in self.cita.values()]
        if not pid or not v[0] or not v[1]:
            return messagebox.showwarning("Faltan datos", "Paciente, fecha y hora son obligatorios.")
        with self.con:
            self.con.execute("INSERT INTO citas(paciente_id, fecha, hora, motivo, estudiante) VALUES (?,?,?,?,?)", (pid, *v))
        for x in self.cita.values():
            x.set("")
        self.refrescar_citas()

    def refrescar_citas(self):
        self.t_cit.delete(*self.t_cit.get_children())
        for fila in self.con.execute("""SELECT c.fecha, c.hora, p.nombre, c.motivo, c.estudiante
                                        FROM citas c JOIN pacientes p ON p.id = c.paciente_id
                                        ORDER BY c.fecha, c.hora"""):
            self.t_cit.insert("", "end", values=fila)

    # ---------- Odontograma ----------
    def tab_odontograma(self, tabs):
        f = ttk.Frame(tabs, padding=10)
        tabs.add(f, text="Odontograma")
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Paciente:").pack(side="left")
        self.odo_paciente = ttk.Combobox(top, state="readonly", width=35)
        self.odo_paciente.pack(side="left", padx=5)
        self.odo_paciente.bind("<<ComboboxSelected>>", lambda e: self.dibujar_odontograma())
        ttk.Label(top, text="Estado a aplicar:").pack(side="left", padx=(20, 5))
        self.estado = ttk.Combobox(top, values=list(ESTADOS), state="readonly", width=12)
        self.estado.set("Caries")
        self.estado.pack(side="left")

        self.canvas = tk.Canvas(f, bg="#eaf4fb", height=300, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=10)

        leyenda = ttk.Frame(f)
        leyenda.pack()
        for nombre, color in ESTADOS.items():
            tk.Label(leyenda, bg=color, width=2, relief="solid", bd=1).pack(side="left", padx=(12, 3))
            ttk.Label(leyenda, text=nombre).pack(side="left")
        self.dibujar_odontograma()

    def dibujar_odontograma(self):
        c = self.canvas
        c.delete("all")
        pid = self.id_de(self.odo_paciente)
        if not pid:
            c.create_text(430, 140, text="Selecciona un paciente para ver su odontograma",
                          font=("Segoe UI", 12), fill="#555")
            return
        estados = dict(self.con.execute("SELECT diente, estado FROM odontograma WHERE paciente_id=?", (pid,)))
        c.create_text(430, 20, text="Superior", font=("Segoe UI", 10, "bold"))
        c.create_text(430, 280, text="Inferior", font=("Segoe UI", 10, "bold"))
        for fila, dientes in enumerate((SUPERIOR, INFERIOR)):
            y = 50 if fila == 0 else 160
            for i, d in enumerate(dientes):
                x = 30 + i * 50 + (10 if i >= 8 else 0)  # separacion en la linea media
                color = ESTADOS[estados.get(d, "Sano")]
                tag = f"d{d}"
                c.create_rectangle(x, y, x + 40, y + 60, fill=color, outline="#34495e", width=2, tags=tag)
                if estados.get(d) == "Extraido":
                    c.create_line(x, y, x + 40, y + 60, width=3, fill="#c0392b", tags=tag)
                    c.create_line(x + 40, y, x, y + 60, width=3, fill="#c0392b", tags=tag)
                c.create_text(x + 20, y + 75, text=str(d), font=("Segoe UI", 9), tags=tag)
                c.tag_bind(tag, "<Button-1>", lambda e, d=d: self.marcar_diente(d))

    def marcar_diente(self, diente):
        with self.con:
            self.con.execute("INSERT OR REPLACE INTO odontograma VALUES (?,?,?)",
                             (self.id_de(self.odo_paciente), diente, self.estado.get()))
        self.dibujar_odontograma()


if __name__ == "__main__":
    App().mainloop()
