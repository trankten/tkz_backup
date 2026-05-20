import os
import sys
import ctypes
import threading
import time
import gzip
import zipfile
import tarfile
import subprocess
import json
import platform
import hashlib
import webbrowser
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

NOMBRE_APP = "TKZ Backup"
VERSION = "1.0"
URL_REPO = "https://github.com/trankten/tkz_backup"
URL_KOFI = "https://ko-fi.com/trankten"

TAMANO_BLOQUE = 16 * 1024 * 1024
COLA_MAX = 4
NIVEL_COMPRESION = 1


def es_admin():
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        return os.geteuid() == 0
    except Exception:
        return False


def relanzar_como_admin():
    if platform.system() != "Windows":
        return
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(0)


def tamano_legible(n):
    n = float(n or 0)
    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unidad}"
        n /= 1024
    return f"{n:.2f} PB"


def _flags_sin_ventana():
    if platform.system() == "Windows":
        return 0x08000000
    return 0


# OJO: usamos los cmdlets nuevos de Storage porque WMI viejo a veces miente con discos USB
def listar_dispositivos_windows():
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$d = Get-Disk | Select-Object Number,FriendlyName,Size,BusType,SerialNumber;"
        "$p = Get-Partition | Select-Object DiskNumber,PartitionNumber,Size,DriveLetter,Type,Offset;"
        "ConvertTo-Json -Compress -Depth 4 -InputObject @{discos=@($d);particiones=@($p)}"
    )
    salida = subprocess.check_output(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        creationflags=_flags_sin_ventana(),
    )
    datos = json.loads(salida.decode("utf-8", errors="ignore").strip() or "{}")
    discos_in = datos.get("discos") or []
    parts_in = datos.get("particiones") or []
    if isinstance(discos_in, dict):
        discos_in = [discos_in]
    if isinstance(parts_in, dict):
        parts_in = [parts_in]
    discos = []
    for d in discos_in:
        num = d.get("Number")
        if num is None:
            continue
        discos.append({
            "tipo": "disco",
            "ruta": f"\\\\.\\PhysicalDrive{num}",
            "modelo": (d.get("FriendlyName") or "Disco").strip(),
            "tamano": int(d.get("Size") or 0),
            "bus": (d.get("BusType") or "").strip() if isinstance(d.get("BusType"), str) else str(d.get("BusType") or ""),
            "indice": num,
            "particiones": [],
        })
    indice_disco = {d["indice"]: d for d in discos}
    for p in parts_in:
        di = p.get("DiskNumber")
        pi = p.get("PartitionNumber")
        if di is None or pi is None or di not in indice_disco:
            continue
        letra = p.get("DriveLetter")
        if isinstance(letra, dict):
            letra = letra.get("Value")
        if letra:
            etiqueta = f"Partición {pi} ({letra}:)"
        else:
            etiqueta = f"Partición {pi}"
        indice_disco[di]["particiones"].append({
            "tipo": "particion",
            "ruta": f"\\\\.\\Harddisk{di}Partition{pi}",
            "modelo": etiqueta,
            "tamano": int(p.get("Size") or 0),
            "bus": str(p.get("Type") or ""),
        })
    return discos


def listar_dispositivos_linux():
    salida = subprocess.check_output(
        ["lsblk", "-J", "-b", "-o", "NAME,SIZE,MODEL,TRAN,TYPE,MOUNTPOINT"]
    )
    datos = json.loads(salida.decode())
    discos = []
    for d in datos.get("blockdevices", []):
        if d.get("type") != "disk":
            continue
        disco = {
            "tipo": "disco",
            "ruta": "/dev/" + d["name"],
            "modelo": (d.get("model") or "Disco").strip(),
            "tamano": int(d.get("size") or 0),
            "bus": (d.get("tran") or "").strip(),
            "particiones": [],
        }
        for hijo in d.get("children", []) or []:
            if hijo.get("type") != "part":
                continue
            mp = hijo.get("mountpoint") or ""
            etiqueta = f"{hijo['name']}" + (f"  [{mp}]" if mp else "")
            disco["particiones"].append({
                "tipo": "particion",
                "ruta": "/dev/" + hijo["name"],
                "modelo": etiqueta,
                "tamano": int(hijo.get("size") or 0),
                "bus": "",
            })
        discos.append(disco)
    return discos


def listar_dispositivos_mac():
    import plistlib
    salida = subprocess.check_output(["diskutil", "list", "-plist", "physical"])
    pl = plistlib.loads(salida)
    discos = []
    for nombre in pl.get("AllDisksAndPartitions", []) or []:
        ruta_disco = "/dev/r" + nombre["DeviceIdentifier"]
        disco = {
            "tipo": "disco",
            "ruta": ruta_disco,
            "modelo": nombre.get("Content") or nombre["DeviceIdentifier"],
            "tamano": int(nombre.get("Size") or 0),
            "bus": "",
            "particiones": [],
        }
        for p in nombre.get("Partitions", []) or []:
            disco["particiones"].append({
                "tipo": "particion",
                "ruta": "/dev/r" + p["DeviceIdentifier"],
                "modelo": p.get("VolumeName") or p["DeviceIdentifier"],
                "tamano": int(p.get("Size") or 0),
                "bus": p.get("Content") or "",
            })
        discos.append(disco)
    return discos


def listar_dispositivos():
    s = platform.system()
    if s == "Windows":
        return listar_dispositivos_windows()
    if s == "Linux":
        return listar_dispositivos_linux()
    if s == "Darwin":
        return listar_dispositivos_mac()
    return []


class _LectorRawWin32:
    def __init__(self, ruta):
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 1
        FILE_SHARE_WRITE = 2
        OPEN_EXISTING = 3
        FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
        FILE_FLAG_NO_BUFFERING = 0x20000000
        k = ctypes.windll.kernel32
        k.CreateFileW.restype = ctypes.c_void_p
        k.CreateFileW.argtypes = [
            ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ]
        # NO_BUFFERING fuerza I/O alineado al sector pero da bastante más velocidad en HDD/SSD
        flags = FILE_FLAG_SEQUENTIAL_SCAN | FILE_FLAG_NO_BUFFERING
        h = k.CreateFileW(
            ruta, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, flags, None,
        )
        invalido = ctypes.c_void_p(-1).value
        if not h or h == invalido:
            raise OSError(f"No se puede abrir {ruta} (Win32 error {ctypes.get_last_error()})")
        self._h = h
        k.ReadFile.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p,
        ]
        k.ReadFile.restype = ctypes.c_int
        k.CloseHandle.argtypes = [ctypes.c_void_p]
        self._buf = (ctypes.c_ubyte * TAMANO_BLOQUE)()

    def read(self, n=-1):
        if n is None or n < 0 or n > TAMANO_BLOQUE:
            n = TAMANO_BLOQUE
        leidos = ctypes.c_uint32(0)
        ok = ctypes.windll.kernel32.ReadFile(
            ctypes.c_void_p(self._h), self._buf, n, ctypes.byref(leidos), None
        )
        if not ok:
            err = ctypes.get_last_error()
            if err and err != 38:
                raise OSError(f"ReadFile error {err}")
        return bytes(self._buf[: leidos.value])

    def close(self):
        try:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self._h))
        except Exception:
            pass


def abrir_dispositivo_raw(ruta):
    if platform.system() == "Windows":
        return _LectorRawWin32(ruta)
    return open(ruta, "rb", buffering=0)


class TrabajadorBackup(threading.Thread):
    def __init__(self, ruta_disp, tamano, salida, formato, calc_hash, cb_progreso, cb_fin):
        super().__init__(daemon=True)
        self.ruta_disp = ruta_disp
        self.total = tamano
        self.salida = salida
        self.formato = formato
        self.calc_hash = calc_hash
        self.cb_progreso = cb_progreso
        self.cb_fin = cb_fin
        self.parar = threading.Event()
        self._copiado = 0
        self._inicio = 0.0
        self.hash_raw = hashlib.sha256() if calc_hash else None

    def cancelar(self):
        self.parar.set()

    def _tick(self):
        self.cb_progreso(self._copiado, self.total, time.time() - self._inicio)

    def _productor(self, src, cola):
        try:
            while not self.parar.is_set():
                datos = src.read(TAMANO_BLOQUE)
                if not datos:
                    break
                cola.put(("d", datos))
        except Exception as e:
            cola.put(("e", e))
        finally:
            cola.put(("f", None))

    def _consumir(self, cola, escritor):
        while True:
            tipo, payload = cola.get()
            if tipo == "f":
                return
            if tipo == "e":
                raise payload
            if self.parar.is_set():
                continue
            if self.hash_raw is not None:
                self.hash_raw.update(payload)
            escritor.write(payload)
            self._copiado += len(payload)
            self._tick()

    def _streaming(self, src, escritor):
        cola = queue.Queue(maxsize=COLA_MAX)
        prod = threading.Thread(target=self._productor, args=(src, cola), daemon=True)
        prod.start()
        try:
            self._consumir(cola, escritor)
        finally:
            self.parar.set()
            prod.join(timeout=2)

    def run(self):
        src = None
        try:
            self._inicio = time.time()
            src = abrir_dispositivo_raw(self.ruta_disp)
            if self.formato == "gz":
                with open(self.salida, "wb", buffering=1024 * 1024) as fout, \
                        gzip.GzipFile(fileobj=fout, mode="wb", compresslevel=NIVEL_COMPRESION) as gz:
                    self._streaming(src, gz)
            elif self.formato == "zip":
                interno = os.path.basename(self.salida)
                if interno.lower().endswith(".zip"):
                    interno = interno[:-4]
                if not interno.lower().endswith(".img"):
                    interno += ".img"
                with zipfile.ZipFile(self.salida, "w", zipfile.ZIP_DEFLATED,
                                     allowZip64=True, compresslevel=NIVEL_COMPRESION) as zf:
                    with zf.open(interno, "w", force_zip64=True) as zo:
                        self._streaming(src, zo)
            elif self.formato == "tar.gz":
                interno = os.path.basename(self.salida)
                bajo = interno.lower()
                if bajo.endswith(".tar.gz"):
                    interno = interno[:-7] + ".img"
                elif bajo.endswith(".tgz"):
                    interno = interno[:-4] + ".img"
                else:
                    interno += ".img"
                # tarfile pide un fileobj con read() de tamaño conocido, así que envolvemos
                trabajo = self

                class _Envoltorio:
                    def read(_s, n=-1):
                        if trabajo.parar.is_set():
                            return b""
                        if n is None or n < 0:
                            n = TAMANO_BLOQUE
                        datos = src.read(n)
                        if datos:
                            if trabajo.hash_raw is not None:
                                trabajo.hash_raw.update(datos)
                            trabajo._copiado += len(datos)
                            trabajo._tick()
                        return datos

                with tarfile.open(self.salida, "w:gz", compresslevel=NIVEL_COMPRESION) as tf:
                    ti = tarfile.TarInfo(name=interno)
                    ti.size = self.total
                    ti.mtime = int(time.time())
                    tf.addfile(ti, _Envoltorio())
            else:
                with open(self.salida, "wb", buffering=1024 * 1024) as fout:
                    self._streaming(src, fout)

            if self.parar.is_set():
                self.cb_fin("cancelado", None)
                return

            hash_hex = self.hash_raw.hexdigest() if self.hash_raw is not None else None
            if hash_hex:
                # sidecar con el hash de los datos crudos para verificar luego
                with open(self.salida + ".sha256", "w", encoding="utf-8") as fh:
                    fh.write(f"{hash_hex}  {os.path.basename(self.salida)}\n")
            self.cb_fin(None, hash_hex)
        except Exception as e:
            self.cb_fin(str(e), None)
        finally:
            try:
                if src is not None:
                    src.close()
            except Exception:
                pass


class VerificadorBackup(threading.Thread):
    def __init__(self, ruta_archivo, hash_esperado, cb_progreso, cb_fin):
        super().__init__(daemon=True)
        self.ruta = ruta_archivo
        self.esperado = (hash_esperado or "").strip().lower() or None
        self.cb_progreso = cb_progreso
        self.cb_fin = cb_fin
        self.parar = threading.Event()

    def cancelar(self):
        self.parar.set()

    def _abrir_stream(self):
        baja = self.ruta.lower()
        if baja.endswith(".gz") and not baja.endswith(".tar.gz"):
            return gzip.open(self.ruta, "rb")
        if baja.endswith(".tar.gz") or baja.endswith(".tgz"):
            tf = tarfile.open(self.ruta, "r:gz")
            miembros = [m for m in tf.getmembers() if m.isfile()]
            if not miembros:
                tf.close()
                raise RuntimeError("El tar no contiene ningún fichero")
            f = tf.extractfile(miembros[0])
            f._tkz_tar = tf
            return f
        if baja.endswith(".zip"):
            zf = zipfile.ZipFile(self.ruta, "r")
            nombres = [n for n in zf.namelist() if not n.endswith("/")]
            if not nombres:
                zf.close()
                raise RuntimeError("El zip está vacío")
            f = zf.open(nombres[0], "r")
            f._tkz_zip = zf
            return f
        return open(self.ruta, "rb")

    def run(self):
        inicio = time.time()
        copiado = 0
        h = hashlib.sha256()
        stream = None
        try:
            stream = self._abrir_stream()
            tam_archivo = os.path.getsize(self.ruta)
            while not self.parar.is_set():
                trozo = stream.read(TAMANO_BLOQUE)
                if not trozo:
                    break
                h.update(trozo)
                copiado += len(trozo)
                self.cb_progreso(copiado, tam_archivo, time.time() - inicio)
            if self.parar.is_set():
                self.cb_fin("cancelado", None, None)
                return
            hex_calc = h.hexdigest()
            if self.esperado is None:
                self.cb_fin(None, hex_calc, None)
            elif hex_calc == self.esperado:
                self.cb_fin(None, hex_calc, True)
            else:
                self.cb_fin(None, hex_calc, False)
        except Exception as e:
            self.cb_fin(str(e), None, None)
        finally:
            try:
                if stream is not None:
                    stream.close()
            except Exception:
                pass


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{NOMBRE_APP} v{VERSION}")
        self.geometry("900x600")
        self.minsize(780, 520)
        self.trabajo = None
        self.dispositivos = []
        self.indice_filas = {}
        self._construir()
        self.after(100, self.refrescar_dispositivos)

    def _construir(self):
        estilo = ttk.Style(self)
        for tema in ("vista", "clam", "default"):
            try:
                estilo.theme_use(tema)
                break
            except Exception:
                continue

        cab = ttk.Frame(self, padding=14)
        cab.pack(fill="x")
        ttk.Label(cab, text=NOMBRE_APP, font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(cab, text=f"v{VERSION}", foreground="#888").pack(side="left", padx=(6, 12))
        ttk.Label(cab, text="Backup de dispositivos con compresión on-the-fly",
                  font=("Segoe UI", 10), foreground="#666").pack(side="left")
        ttk.Button(cab, text="❤ Ko-fi",
                   command=lambda: webbrowser.open(URL_KOFI)).pack(side="right")
        ttk.Button(cab, text="GitHub",
                   command=lambda: webbrowser.open(URL_REPO)).pack(side="right", padx=6)
        ttk.Button(cab, text="Refrescar",
                   command=self.refrescar_dispositivos).pack(side="right", padx=6)

        ppal = ttk.Frame(self, padding=(14, 0, 14, 14))
        ppal.pack(fill="both", expand=True)

        cols = ("ruta", "modelo", "tamano", "bus")
        self.arbol = ttk.Treeview(ppal, columns=cols, show="tree headings", height=12)
        self.arbol.heading("#0", text="")
        self.arbol.column("#0", width=24, stretch=False)
        for c, t, w, anc in (
            ("ruta", "Dispositivo", 220, "w"),
            ("modelo", "Modelo / Partición", 320, "w"),
            ("tamano", "Tamaño", 120, "e"),
            ("bus", "Bus / Tipo", 120, "w"),
        ):
            self.arbol.heading(c, text=t)
            self.arbol.column(c, width=w, anchor=anc)
        self.arbol.pack(fill="both", expand=True, pady=(0, 10))

        ops = ttk.LabelFrame(ppal, text="Opciones", padding=10)
        ops.pack(fill="x", pady=(0, 8))
        ttk.Label(ops, text="Formato:").pack(side="left")
        self.formato = tk.StringVar(value="gz")
        for etiqueta, val in (
            ("img.gz", "gz"),
            ("img.zip", "zip"),
            ("img.tar.gz", "tar.gz"),
            ("img (sin comprimir)", "raw"),
        ):
            ttk.Radiobutton(ops, text=etiqueta, variable=self.formato, value=val).pack(side="left", padx=6)
        self.calc_hash = tk.BooleanVar(value=True)
        ttk.Checkbutton(ops, text="Calcular SHA-256 (verificable)",
                        variable=self.calc_hash).pack(side="left", padx=(20, 0))

        acc = ttk.Frame(ppal)
        acc.pack(fill="x", pady=(0, 8))
        self.btn_crear = ttk.Button(acc, text="Crear backup…", command=self.iniciar_backup)
        self.btn_crear.pack(side="right")
        self.btn_verificar = ttk.Button(acc, text="Verificar backup…", command=self.iniciar_verificacion)
        self.btn_verificar.pack(side="right", padx=6)
        self.btn_cancelar = ttk.Button(acc, text="Cancelar", command=self.cancelar, state="disabled")
        self.btn_cancelar.pack(side="right", padx=6)

        self.barra = ttk.Progressbar(ppal, mode="determinate", maximum=1000)
        self.barra.pack(fill="x")
        txt = "Listo." if es_admin() else "AVISO: se requieren permisos de Administrador."
        self.estado = ttk.Label(ppal, text=txt, anchor="w")
        self.estado.pack(fill="x", pady=(8, 0))

    def refrescar_dispositivos(self):
        for hijo in self.arbol.get_children():
            self.arbol.delete(hijo)
        self.indice_filas.clear()
        try:
            self.dispositivos = listar_dispositivos()
        except Exception as e:
            messagebox.showerror(NOMBRE_APP, f"Error al listar dispositivos:\n{e}")
            self.dispositivos = []
            return
        for d in self.dispositivos:
            id_disco = self.arbol.insert(
                "", "end", open=True,
                values=(d["ruta"], d["modelo"], tamano_legible(d["tamano"]), d.get("bus", "")),
            )
            self.indice_filas[id_disco] = d
            for p in d.get("particiones", []):
                id_part = self.arbol.insert(
                    id_disco, "end",
                    values=(p["ruta"], p["modelo"], tamano_legible(p["tamano"]), p.get("bus", "")),
                )
                self.indice_filas[id_part] = p
        self.estado.configure(text=f"{len(self.dispositivos)} disco(s) detectado(s).")

    def _seleccionado(self):
        sel = self.arbol.selection()
        if not sel:
            return None
        return self.indice_filas.get(sel[0])

    def iniciar_backup(self):
        if not es_admin():
            messagebox.showerror(NOMBRE_APP, "Se requieren permisos de Administrador para leer dispositivos.")
            return
        d = self._seleccionado()
        if not d:
            messagebox.showinfo(NOMBRE_APP, "Selecciona un disco o partición de la lista.")
            return
        if not d.get("tamano"):
            if not messagebox.askyesno(NOMBRE_APP, "No se conoce el tamaño. ¿Continuar?"):
                return
        f = self.formato.get()
        ext = {"gz": ".img.gz", "zip": ".img.zip", "tar.gz": ".img.tar.gz", "raw": ".img"}[f]
        nombre_seguro = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in (d["modelo"] or "device")
        )[:40] or "device"
        sufijo = "_part" if d.get("tipo") == "particion" else ""
        por_defecto = f"tkz_backup_{nombre_seguro}{sufijo}{ext}"
        salida = filedialog.asksaveasfilename(
            title="Guardar backup como…",
            defaultextension=ext,
            initialfile=por_defecto,
            filetypes=[("TKZ Backup", "*" + ext), ("Todos", "*.*")],
        )
        if not salida:
            return
        confirmar = messagebox.askyesno(
            NOMBRE_APP,
            f"Crear backup de:\n  {d['ruta']}\n  {d['modelo']}  ({tamano_legible(d['tamano'])})\n\n"
            f"Destino:\n  {salida}\n\n¿Continuar?",
        )
        if not confirmar:
            return
        self.barra["value"] = 0
        self.btn_crear.configure(state="disabled")
        self.btn_verificar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.estado.configure(text=f"Iniciando backup de {d['ruta']}…")
        self.trabajo = TrabajadorBackup(
            d["ruta"], d["tamano"], salida, f,
            self.calc_hash.get(), self._cb_progreso, self._cb_fin_backup,
        )
        self.trabajo.start()

    def iniciar_verificacion(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el backup a verificar…",
            filetypes=[
                ("TKZ Backup", "*.gz *.zip *.tgz *.img"),
                ("Todos", "*.*"),
            ],
        )
        if not ruta:
            return
        esperado = None
        sidecar = ruta + ".sha256"
        if os.path.exists(sidecar):
            try:
                with open(sidecar, "r", encoding="utf-8") as fh:
                    esperado = fh.read().split()[0]
            except Exception:
                esperado = None
        else:
            if messagebox.askyesno(NOMBRE_APP,
                                   "No se encontró el sidecar .sha256.\n"
                                   "¿Introducir el hash manualmente?"):
                dlg = tk.Toplevel(self)
                dlg.title("Hash SHA-256")
                dlg.transient(self)
                dlg.grab_set()
                tk.Label(dlg, text="SHA-256 esperado (deja vacío para solo calcular):").pack(padx=12, pady=(12, 4))
                ent = tk.Entry(dlg, width=72)
                ent.pack(padx=12, pady=(0, 8))
                resultado = {"v": None}

                def ok():
                    resultado["v"] = ent.get().strip()
                    dlg.destroy()
                ttk.Button(dlg, text="OK", command=ok).pack(pady=(0, 12))
                self.wait_window(dlg)
                esperado = resultado["v"] or None
        self.barra["value"] = 0
        self.btn_crear.configure(state="disabled")
        self.btn_verificar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.estado.configure(text=f"Verificando {os.path.basename(ruta)}…")
        self.trabajo = VerificadorBackup(ruta, esperado, self._cb_progreso, self._cb_fin_verif)
        self.trabajo.start()

    def cancelar(self):
        if self.trabajo:
            self.trabajo.cancelar()
            self.estado.configure(text="Cancelando…")

    def _cb_progreso(self, copiado, total, transcurrido):
        def upd():
            pct = (copiado / total) if total else 0
            self.barra["value"] = min(1000, pct * 1000)
            vel = (copiado / transcurrido / (1024 * 1024)) if transcurrido > 0 else 0
            eta = ""
            if vel > 0 and total:
                rest = max(0, (total - copiado) / (vel * 1024 * 1024))
                m, s = divmod(int(rest), 60)
                h, m = divmod(m, 60)
                eta = f"  ·  ETA {h:02d}:{m:02d}:{s:02d}"
            self.estado.configure(
                text=f"{tamano_legible(copiado)} / {tamano_legible(total)}  "
                     f"({pct*100:.1f}%)  ·  {vel:.1f} MB/s{eta}"
            )
        self.after(0, upd)

    def _resetear_botones(self):
        self.btn_crear.configure(state="normal")
        self.btn_verificar.configure(state="normal")
        self.btn_cancelar.configure(state="disabled")

    def _cb_fin_backup(self, err, hash_hex):
        def upd():
            self._resetear_botones()
            if err is None:
                self.barra["value"] = 1000
                msg = "Backup completado correctamente."
                if hash_hex:
                    msg += f"\n\nSHA-256:\n{hash_hex}\n\nGuardado en .sha256 junto al backup."
                self.estado.configure(text="Backup completado.")
                messagebox.showinfo(NOMBRE_APP, msg)
            elif err == "cancelado":
                self.estado.configure(text="Cancelado por el usuario.")
            else:
                self.estado.configure(text=f"Error: {err}")
                messagebox.showerror(NOMBRE_APP, err)
        self.after(0, upd)

    def _cb_fin_verif(self, err, hex_calc, coincide):
        def upd():
            self._resetear_botones()
            if err == "cancelado":
                self.estado.configure(text="Verificación cancelada.")
                return
            if err is not None:
                self.estado.configure(text=f"Error: {err}")
                messagebox.showerror(NOMBRE_APP, err)
                return
            self.barra["value"] = 1000
            if coincide is None:
                self.estado.configure(text="Hash calculado (sin comparar).")
                messagebox.showinfo(NOMBRE_APP, f"SHA-256 calculado:\n{hex_calc}")
            elif coincide:
                self.estado.configure(text="Integridad OK ✓")
                messagebox.showinfo(NOMBRE_APP, f"Integridad verificada correctamente.\n\nSHA-256:\n{hex_calc}")
            else:
                self.estado.configure(text="Integridad FALLIDA ✗")
                messagebox.showerror(NOMBRE_APP, f"El hash NO coincide.\n\nCalculado:\n{hex_calc}")
        self.after(0, upd)


def principal():
    if platform.system() == "Windows" and not es_admin():
        relanzar_como_admin()
        return
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    principal()
