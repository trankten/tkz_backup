import os
import sys
import re
import ctypes
import threading
import time
import gzip
import zipfile
import tarfile
import shutil
import subprocess
import json
import platform
import hashlib
import webbrowser
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

NOMBRE_APP = "TKZ Backup"
VERSION = "1.1"
URL_REPO = "https://github.com/trankten/tkz_backup"
URL_KOFI = "https://ko-fi.com/trankten"

TAMANO_BLOQUE = 16 * 1024 * 1024
COLA_MAX = 4
NIVEL_COMPRESION = 1

# Rutas típicas donde los fabricantes dejan instaladores originales de drivers
# (oro puro cuando el fabricante ya no da soporte o ha desaparecido)
RUTAS_OEM_INSTALADORES = [
    "Drivers",
    "SWSetup",
    "SWTOOLS",
    "OEM",
    "Dell",
    "Intel",
    "AMD",
    "NVIDIA",
    "MSI",
    "ASUS",
    "Lenovo",
    "HP",
]

TRADUCCIONES = {
    "es": {
        "subtitulo": "Backup de dispositivos con compresión on-the-fly",
        "refrescar": "Refrescar",
        "github": "GitHub",
        "kofi": "❤ Ko-fi",
        "buscar_windows": "Buscar OS Windows",
        "opciones": "Opciones",
        "formato": "Formato:",
        "calc_hash": "Calcular SHA-256 (verificable)",
        "crear_backup": "Crear backup…",
        "verificar_backup": "Verificar backup…",
        "cancelar": "Cancelar",
        "listo": "Listo.",
        "aviso_admin": "AVISO: se requieren permisos de Administrador.",
        "col_disp": "Dispositivo",
        "col_modelo": "Modelo / Partición",
        "col_tam": "Tamaño",
        "col_bus": "Bus / Tipo",
        "n_discos": "{n} disco(s) detectado(s).",
        "err_listar": "Error al listar dispositivos:\n{e}",
        "err_admin": "Se requieren permisos de Administrador para leer dispositivos.",
        "sel_disp": "Selecciona un disco o partición de la lista.",
        "tam_desconocido": "No se conoce el tamaño. ¿Continuar?",
        "guardar_como": "Guardar backup como…",
        "confirmar_backup": "Crear backup de:\n  {r}\n  {m}  ({t})\n\nDestino:\n  {o}\n\n¿Continuar?",
        "iniciando": "Iniciando backup de {r}…",
        "completado_msg": "Backup completado correctamente.",
        "sha_guardado": "\n\nSHA-256:\n{h}\n\nGuardado en .sha256 junto al backup.",
        "estado_completado": "Backup completado.",
        "cancelado_user": "Cancelado por el usuario.",
        "cancelando": "Cancelando…",
        "sel_verificar": "Selecciona el backup a verificar…",
        "no_sidecar": "No se encontró el sidecar .sha256.\n¿Introducir el hash manualmente?",
        "hash_label": "SHA-256 esperado (deja vacío para solo calcular):",
        "verificando": "Verificando {f}…",
        "verif_cancelada": "Verificación cancelada.",
        "hash_calculado": "Hash calculado (sin comparar).",
        "hash_msg": "SHA-256 calculado:\n{h}",
        "integ_ok": "Integridad OK ✓",
        "integ_ok_msg": "Integridad verificada correctamente.\n\nSHA-256:\n{h}",
        "integ_fail": "Integridad FALLIDA ✗",
        "integ_fail_msg": "El hash NO coincide.\n\nCalculado:\n{h}",
        "buscando_win": "Buscando instalaciones Windows…",
        "win_no_encontradas": "No se han encontrado instalaciones de Windows.\n\n"
            "Sólo se pueden inspeccionar particiones con letra de unidad asignada y "
            "sistema de ficheros legible. Si la partición no tiene letra, asígnale una "
            "desde el Administrador de discos.",
        "win_encontradas": "Instalaciones de Windows detectadas",
        "win_partition": "Partición {l}:  ({v})",
        "btn_backup_drivers": "Backup Drivers",
        "drivers_titulo": "Backup de drivers",
        "drivers_modo": "Formato de salida:",
        "drivers_carpeta": "Carpeta (recomendado para reinstalación directa)",
        "drivers_zip": "ZIP único (recomendado para archivar / transportar)",
        "drivers_alcance": "Alcance:",
        "drivers_alcance_completo": "Completo: DriverStore + OEM .inf + binarios .sys + catálogos + instaladores OEM",
        "drivers_alcance_rapido": "Sólo DriverStore (rápido)",
        "drivers_sel_carpeta": "Selecciona la carpeta destino para los drivers",
        "drivers_sel_zip": "Guardar drivers como ZIP",
        "drivers_iniciando": "Copiando drivers de {l}: …",
        "drivers_progreso": "{f} ficheros  ·  {n} paquetes  ·  {t}",
        "drivers_completado_t": "Backup de drivers finalizado",
        "drivers_completado": "Backup de drivers finalizado.\n\nPaquetes: {n}\nFicheros: {f}\nTamaño copiado: {t}\n\nDestino:\n{d}",
        "drivers_error": "Error al copiar drivers:\n{e}",
        "drivers_no_windows": "Esta partición no contiene una instalación de Windows válida.",
        "iniciar": "Iniciar",
        "cerrar": "Cerrar",
        "idioma": "Idioma:",
        "formato_sin_comp": "img (sin comprimir)",
        "ttl_aviso": NOMBRE_APP,
    },
    "en": {
        "subtitulo": "Device backup with on-the-fly compression",
        "refrescar": "Refresh",
        "github": "GitHub",
        "kofi": "❤ Ko-fi",
        "buscar_windows": "Find Windows OS",
        "opciones": "Options",
        "formato": "Format:",
        "calc_hash": "Compute SHA-256 (verifiable)",
        "crear_backup": "Create backup…",
        "verificar_backup": "Verify backup…",
        "cancelar": "Cancel",
        "listo": "Ready.",
        "aviso_admin": "WARNING: Administrator privileges are required.",
        "col_disp": "Device",
        "col_modelo": "Model / Partition",
        "col_tam": "Size",
        "col_bus": "Bus / Type",
        "n_discos": "{n} disk(s) detected.",
        "err_listar": "Error listing devices:\n{e}",
        "err_admin": "Administrator privileges are required to read devices.",
        "sel_disp": "Select a disk or partition from the list.",
        "tam_desconocido": "Device size is unknown. Continue anyway?",
        "guardar_como": "Save backup as…",
        "confirmar_backup": "Create backup of:\n  {r}\n  {m}  ({t})\n\nDestination:\n  {o}\n\nContinue?",
        "iniciando": "Starting backup of {r}…",
        "completado_msg": "Backup completed successfully.",
        "sha_guardado": "\n\nSHA-256:\n{h}\n\nSaved in a .sha256 sidecar next to the backup.",
        "estado_completado": "Backup completed.",
        "cancelado_user": "Cancelled by the user.",
        "cancelando": "Cancelling…",
        "sel_verificar": "Select the backup to verify…",
        "no_sidecar": "No .sha256 sidecar found.\nDo you want to enter the hash manually?",
        "hash_label": "Expected SHA-256 (leave empty to only compute):",
        "verificando": "Verifying {f}…",
        "verif_cancelada": "Verification cancelled.",
        "hash_calculado": "Hash computed (not compared).",
        "hash_msg": "SHA-256 computed:\n{h}",
        "integ_ok": "Integrity OK ✓",
        "integ_ok_msg": "Integrity verified successfully.\n\nSHA-256:\n{h}",
        "integ_fail": "Integrity FAILED ✗",
        "integ_fail_msg": "Hash does NOT match.\n\nComputed:\n{h}",
        "buscando_win": "Searching for Windows installations…",
        "win_no_encontradas": "No Windows installations found.\n\n"
            "Only partitions with an assigned drive letter and a readable file system "
            "can be inspected. If the partition has no letter, assign one from Disk Manager.",
        "win_encontradas": "Detected Windows installations",
        "win_partition": "Partition {l}:  ({v})",
        "btn_backup_drivers": "Backup Drivers",
        "drivers_titulo": "Driver backup",
        "drivers_modo": "Output format:",
        "drivers_carpeta": "Folder (recommended for direct reinstall)",
        "drivers_zip": "Single ZIP (recommended for archiving / transport)",
        "drivers_alcance": "Scope:",
        "drivers_alcance_completo": "Full: DriverStore + OEM .inf + .sys binaries + catalogs + OEM installers",
        "drivers_alcance_rapido": "DriverStore only (fast)",
        "drivers_sel_carpeta": "Select the destination folder for the drivers",
        "drivers_sel_zip": "Save drivers as ZIP",
        "drivers_iniciando": "Copying drivers from {l}: …",
        "drivers_progreso": "{f} files  ·  {n} packages  ·  {t}",
        "drivers_completado_t": "Driver backup finished",
        "drivers_completado": "Driver backup finished.\n\nPackages: {n}\nFiles: {f}\nSize copied: {t}\n\nDestination:\n{d}",
        "drivers_error": "Error copying drivers:\n{e}",
        "drivers_no_windows": "This partition does not contain a valid Windows installation.",
        "iniciar": "Start",
        "cerrar": "Close",
        "idioma": "Language:",
        "formato_sin_comp": "img (uncompressed)",
        "ttl_aviso": NOMBRE_APP,
    },
}

idioma_actual = "es"


def t(clave, **kw):
    val = TRADUCCIONES.get(idioma_actual, {}).get(clave)
    if val is None:
        val = TRADUCCIONES["en"].get(clave, clave)
    if kw:
        try:
            return val.format(**kw)
        except Exception:
            return val
    return val


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
        bus = d.get("BusType")
        discos.append({
            "tipo": "disco",
            "ruta": f"\\\\.\\PhysicalDrive{num}",
            "modelo": (d.get("FriendlyName") or "Disco").strip(),
            "tamano": int(d.get("Size") or 0),
            "bus": bus if isinstance(bus, str) else str(bus or ""),
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
        if isinstance(letra, int):
            letra = chr(letra) if letra > 31 else None
        if letra:
            letra = str(letra).strip("\x00 ").upper()
            if not letra or not letra[0].isalpha():
                letra = None
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
            "letra": letra,
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
                "letra": mp or None,
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
                "letra": None,
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


def detectar_windows_en_particion(letra):
    if not letra:
        return None
    base = f"{letra}:\\" if platform.system() == "Windows" else letra
    sis = os.path.join(base, "Windows", "System32", "config", "SYSTEM")
    if not os.path.exists(sis):
        return None
    ver = "Windows"
    ver_dir = os.path.join(base, "Windows", "servicing", "Version")
    if os.path.isdir(ver_dir):
        try:
            vs = [n for n in os.listdir(ver_dir) if os.path.isdir(os.path.join(ver_dir, n))]
            vs.sort(key=lambda s: [int(x) if x.isdigit() else 0 for x in re.split(r"[.]", s)])
            if vs:
                v = vs[-1]
                major = v.split(".")[0]
                # heurística rápida: 10.0.10xxx -> Win10, 10.0.22xxx -> Win11, 6.x -> Win7/8
                if major == "10":
                    build = v.split(".")[2] if len(v.split(".")) >= 3 else ""
                    if build and build.isdigit() and int(build) >= 22000:
                        ver = f"Windows 11 ({v})"
                    else:
                        ver = f"Windows 10 ({v})"
                elif major == "6":
                    ver = f"Windows 7/8 ({v})"
                else:
                    ver = f"Windows {v}"
        except OSError:
            pass
    return ver


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
        # NO_BUFFERING fuerza I/O alineado al sector pero da bastante más velocidad
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


def _parsear_inf(ruta_inf):
    # parser minimalista de .inf: sólo extraemos los campos típicos de [Version]
    info = {"Provider": "", "Class": "", "DriverVer": "", "CatalogFile": ""}
    seccion = ""
    try:
        with open(ruta_inf, "r", encoding="utf-16", errors="ignore") as fh:
            datos = fh.read()
    except Exception:
        try:
            with open(ruta_inf, "r", encoding="latin-1", errors="ignore") as fh:
                datos = fh.read()
        except Exception:
            return info
    for linea in datos.splitlines():
        bruta = linea.strip()
        if not bruta or bruta.startswith(";"):
            continue
        if bruta.startswith("[") and bruta.endswith("]"):
            seccion = bruta[1:-1].strip().lower()
            continue
        if seccion != "version":
            continue
        if "=" not in bruta:
            continue
        k, _, v = bruta.partition("=")
        k = k.strip()
        v = v.split(";", 1)[0].strip().strip('"')
        if k in info and not info[k]:
            info[k] = v
    return info


LEEME_DRIVERS_ES = """TKZ Backup — Backup de drivers de una instalación Windows
==========================================================

Contenido de este backup:
  FileRepository/         Paquetes de drivers del DriverStore (todos los drivers
                          de terceros instalados por Plug and Play).
  INF/                    Copias indexadas oem*.inf + oem*.PNF que mapean cada
                          paquete del DriverStore con el dispositivo que lo usa.
  System32_drivers/       Binarios .sys cargados por el kernel. Importante para
                          drivers legacy (Windows 7) que no usan DriverStore.
  CatRoot/                Catálogos de firma digital (.cat). Sin ellos algunas
                          firmas de drivers no pueden verificarse al reinstalar.
  OEM_Installers/         Instaladores originales del fabricante que estaban
                          guardados en carpetas tipo C:\\Drivers, C:\\SWSetup,
                          C:\\Dell\\Drivers, C:\\SWTOOLS\\DRIVERS, C:\\OEM…
                          Son ORO PURO cuando el fabricante ya no existe.
  manifest.json           Listado de todos los paquetes con Provider / Class /
                          DriverVer / CatalogFile parseado de cada .inf.

Cómo reinstalar en otro Windows
-------------------------------
1) Copia (o extrae) la carpeta FileRepository a, por ejemplo, C:\\TKZ_Drivers
2) Abre PowerShell como Administrador y ejecuta:

   pnputil /add-driver C:\\TKZ_Drivers\\FileRepository\\*\\*.inf /subdirs /install

   Esto añade todos los paquetes al DriverStore del nuevo sistema y, donde sea
   posible, los instala para los dispositivos detectados.

3) Si algún dispositivo concreto no recoge el driver automáticamente:
   - Administrador de dispositivos -> botón derecho sobre el dispositivo
     amarillo -> Actualizar controlador -> Buscar en mi equipo -> apuntar a
     C:\\TKZ_Drivers\\FileRepository (marca "incluir subcarpetas").

4) Para drivers OEM con instalador propio mira en OEM_Installers/, ejecuta los
   .exe o .msi correspondientes (suelen ser drivers de chipset, control de
   ventiladores, lectores de huella, hotkeys, etc).
"""

LEEME_DRIVERS_EN = """TKZ Backup — Driver backup from a Windows installation
=======================================================

Contents of this backup:
  FileRepository/         Driver packages from the DriverStore (all 3rd-party
                          drivers installed by Plug and Play).
  INF/                    Indexed oem*.inf + oem*.PNF mapping each DriverStore
                          package to the device that uses it.
  System32_drivers/       .sys binaries loaded by the kernel. Important for
                          legacy drivers (Windows 7) that don't use DriverStore.
  CatRoot/                Driver signature catalogs (.cat). Without them some
                          signatures cannot be verified on reinstall.
  OEM_Installers/         Original vendor installers found in folders such as
                          C:\\Drivers, C:\\SWSetup, C:\\Dell\\Drivers,
                          C:\\SWTOOLS\\DRIVERS, C:\\OEM…
                          GOLD when the vendor no longer exists.
  manifest.json           List of all packages with Provider / Class /
                          DriverVer / CatalogFile parsed from each .inf.

How to reinstall on another Windows
-----------------------------------
1) Copy (or extract) the FileRepository folder to, e.g., C:\\TKZ_Drivers
2) Open PowerShell as Administrator and run:

   pnputil /add-driver C:\\TKZ_Drivers\\FileRepository\\*\\*.inf /subdirs /install

3) For specific devices not picked up automatically, use Device Manager ->
   Update driver -> Browse my computer -> point to C:\\TKZ_Drivers\\FileRepository
   (check "Include subfolders").

4) For OEM drivers with their own installer, see OEM_Installers/ and run the
   matching .exe / .msi (chipset, fan control, fingerprint readers, hotkeys…).
"""


class TrabajadorDrivers(threading.Thread):
    def __init__(self, letra, destino, modo, completo, cb_progreso, cb_fin):
        super().__init__(daemon=True)
        self.letra = letra
        self.destino = destino
        self.modo = modo
        self.completo = completo
        self.cb_progreso = cb_progreso
        self.cb_fin = cb_fin
        self.parar = threading.Event()
        self.ficheros = 0
        self.paquetes = 0
        self.bytes = 0
        self._zip = None
        self._dest_dir = None
        self._manifest = []

    def cancelar(self):
        self.parar.set()

    def _tick(self):
        self.cb_progreso(self.ficheros, self.paquetes, self.bytes)

    def _escribir_fichero(self, ruta_src, arcname):
        if self.parar.is_set():
            return
        try:
            tam = os.path.getsize(ruta_src)
        except OSError:
            return
        try:
            if self._zip is not None:
                self._zip.write(ruta_src, arcname)
            else:
                destino_full = os.path.join(self._dest_dir, arcname.replace("/", os.sep))
                os.makedirs(os.path.dirname(destino_full), exist_ok=True)
                shutil.copy2(ruta_src, destino_full)
        except (OSError, PermissionError):
            return
        self.ficheros += 1
        self.bytes += tam
        if self.ficheros % 50 == 0:
            self._tick()

    def _escribir_texto(self, arcname, texto):
        if self._zip is not None:
            self._zip.writestr(arcname, texto)
        else:
            destino_full = os.path.join(self._dest_dir, arcname.replace("/", os.sep))
            os.makedirs(os.path.dirname(destino_full) or self._dest_dir, exist_ok=True)
            with open(destino_full, "w", encoding="utf-8") as f:
                f.write(texto)

    def _copiar_arbol(self, raiz_src, prefijo_dest, indexar_inf=False):
        if not os.path.isdir(raiz_src):
            return
        for dirpath, dirnames, filenames in os.walk(raiz_src):
            if self.parar.is_set():
                return
            # nos saltamos carpetas de telemetría / temporales que no aportan
            dirnames[:] = [d for d in dirnames if d.lower() not in (
                "$recycle.bin", "system volume information", "windowsapps")]
            for nombre in filenames:
                if self.parar.is_set():
                    return
                full = os.path.join(dirpath, nombre)
                rel = os.path.relpath(full, raiz_src).replace("\\", "/")
                arc = f"{prefijo_dest}/{rel}"
                if indexar_inf and nombre.lower().endswith(".inf"):
                    info = _parsear_inf(full)
                    info["inf"] = arc
                    info["package_dir"] = os.path.basename(os.path.dirname(full))
                    self._manifest.append(info)
                self._escribir_fichero(full, arc)
            # contamos un "paquete" por cada subcarpeta directa de FileRepository
            if indexar_inf and os.path.normpath(dirpath) != os.path.normpath(raiz_src):
                rel_dir = os.path.relpath(dirpath, raiz_src)
                if os.sep not in rel_dir and rel_dir != ".":
                    pass

    def run(self):
        try:
            base = f"{self.letra}:\\"
            if not os.path.isdir(os.path.join(base, "Windows")):
                self.cb_fin(t("drivers_no_windows"), self.paquetes, self.ficheros, self.bytes)
                return

            if self.modo == "zip":
                self._zip = zipfile.ZipFile(
                    self.destino, "w", zipfile.ZIP_DEFLATED,
                    allowZip64=True, compresslevel=NIVEL_COMPRESION,
                )
            else:
                self._dest_dir = self.destino
                os.makedirs(self._dest_dir, exist_ok=True)

            try:
                # 1) DriverStore\FileRepository (núcleo)
                store = os.path.join(base, "Windows", "System32", "DriverStore", "FileRepository")
                if os.path.isdir(store):
                    try:
                        self.paquetes = sum(
                            1 for n in os.listdir(store)
                            if os.path.isdir(os.path.join(store, n))
                        )
                    except OSError:
                        pass
                    self._copiar_arbol(store, "FileRepository", indexar_inf=True)

                if self.completo and not self.parar.is_set():
                    # 2) Windows\INF (oem*.inf, oem*.PNF, setupapi logs)
                    inf_dir = os.path.join(base, "Windows", "INF")
                    if os.path.isdir(inf_dir):
                        for nombre in os.listdir(inf_dir):
                            full = os.path.join(inf_dir, nombre)
                            if not os.path.isfile(full):
                                continue
                            low = nombre.lower()
                            if (low.startswith("oem") and (low.endswith(".inf") or low.endswith(".pnf"))) \
                                    or low.startswith("setupapi"):
                                self._escribir_fichero(full, f"INF/{nombre}")

                    # 3) System32\drivers\*.sys (binarios kernel)
                    drv_dir = os.path.join(base, "Windows", "System32", "drivers")
                    if os.path.isdir(drv_dir):
                        for nombre in os.listdir(drv_dir):
                            if self.parar.is_set():
                                break
                            full = os.path.join(drv_dir, nombre)
                            if os.path.isfile(full) and nombre.lower().endswith((".sys", ".dll")):
                                self._escribir_fichero(full, f"System32_drivers/{nombre}")

                    # 4) CatRoot (catálogos de firma)
                    cat_dir = os.path.join(base, "Windows", "System32", "CatRoot")
                    if os.path.isdir(cat_dir):
                        self._copiar_arbol(cat_dir, "CatRoot")

                    # 5) Instaladores OEM en raíz — aquí está el oro de fabricantes muertos
                    for nombre in RUTAS_OEM_INSTALADORES:
                        candidato = os.path.join(base, nombre)
                        if os.path.isdir(candidato):
                            self._copiar_arbol(candidato, f"OEM_Installers/{nombre}")

                    # 6) ProgramData de algunos fabricantes (Dell SupportAssist guarda drivers)
                    pdata = os.path.join(base, "ProgramData")
                    if os.path.isdir(pdata):
                        for marca in ("Dell", "HP", "Lenovo", "ASUS", "MSI"):
                            cand = os.path.join(pdata, marca)
                            if os.path.isdir(cand):
                                self._copiar_arbol(cand, f"OEM_Installers/ProgramData_{marca}")

                # manifest + leeme
                self._escribir_texto("manifest.json", json.dumps({
                    "app": NOMBRE_APP,
                    "version": VERSION,
                    "letra_origen": self.letra,
                    "creado": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "paquetes": self._manifest,
                    "totales": {
                        "ficheros": self.ficheros,
                        "bytes": self.bytes,
                        "paquetes_filerepo": self.paquetes,
                    },
                }, indent=2, ensure_ascii=False))
                self._escribir_texto("LEEME.txt", LEEME_DRIVERS_ES)
                self._escribir_texto("README.txt", LEEME_DRIVERS_EN)
            finally:
                if self._zip is not None:
                    self._zip.close()

            if self.parar.is_set():
                self.cb_fin("cancelado", self.paquetes, self.ficheros, self.bytes)
            else:
                self.cb_fin(None, self.paquetes, self.ficheros, self.bytes)
        except Exception as e:
            self.cb_fin(str(e), self.paquetes, self.ficheros, self.bytes)


class DialogoBackupDrivers(tk.Toplevel):
    def __init__(self, padre, letra, version):
        super().__init__(padre)
        self.padre = padre
        self.letra = letra
        self.version = version
        self.title(f"{t('drivers_titulo')} — {letra}: ({version})")
        self.transient(padre)
        self.grab_set()
        self.geometry("620x340")
        self.resizable(False, False)
        self.trabajo = None
        self._construir()

    def _construir(self):
        cont = ttk.Frame(self, padding=14)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text=f"{self.letra}:  —  {self.version}",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")

        ttk.Label(cont, text=t("drivers_modo")).pack(anchor="w", pady=(10, 2))
        self.modo = tk.StringVar(value="carpeta")
        ttk.Radiobutton(cont, text=t("drivers_carpeta"), variable=self.modo, value="carpeta").pack(anchor="w")
        ttk.Radiobutton(cont, text=t("drivers_zip"), variable=self.modo, value="zip").pack(anchor="w")

        ttk.Label(cont, text=t("drivers_alcance")).pack(anchor="w", pady=(10, 2))
        self.completo = tk.BooleanVar(value=True)
        ttk.Radiobutton(cont, text=t("drivers_alcance_completo"),
                        variable=self.completo, value=True).pack(anchor="w")
        ttk.Radiobutton(cont, text=t("drivers_alcance_rapido"),
                        variable=self.completo, value=False).pack(anchor="w")

        self.barra = ttk.Progressbar(cont, mode="indeterminate")
        self.barra.pack(fill="x", pady=(14, 4))
        self.estado = ttk.Label(cont, text="")
        self.estado.pack(anchor="w")

        botones = ttk.Frame(cont)
        botones.pack(fill="x", pady=(10, 0))
        self.btn_iniciar = ttk.Button(botones, text=t("iniciar"), command=self.iniciar)
        self.btn_iniciar.pack(side="right")
        self.btn_cerrar = ttk.Button(botones, text=t("cerrar"), command=self.destroy)
        self.btn_cerrar.pack(side="right", padx=6)

    def iniciar(self):
        if self.modo.get() == "zip":
            destino = filedialog.asksaveasfilename(
                parent=self,
                title=t("drivers_sel_zip"),
                defaultextension=".zip",
                initialfile=f"TKZ_Drivers_{self.letra}.zip",
                filetypes=[("ZIP", "*.zip")],
            )
        else:
            destino = filedialog.askdirectory(parent=self, title=t("drivers_sel_carpeta"),
                                              mustexist=False)
            if destino:
                destino = os.path.join(destino, f"TKZ_Drivers_{self.letra}")
        if not destino:
            return
        self.btn_iniciar.configure(state="disabled")
        self.barra.start(60)
        self.estado.configure(text=t("drivers_iniciando", l=self.letra))
        self.trabajo = TrabajadorDrivers(
            self.letra, destino, self.modo.get(), self.completo.get(),
            self._cb_progreso, self._cb_fin,
        )
        self.trabajo.start()

    def _cb_progreso(self, ficheros, paquetes, bts):
        def upd():
            self.estado.configure(text=t("drivers_progreso",
                                          f=ficheros, n=paquetes, t=tamano_legible(bts)))
        self.after(0, upd)

    def _cb_fin(self, err, paquetes, ficheros, bts):
        def upd():
            self.barra.stop()
            self.barra.configure(mode="determinate", value=100, maximum=100)
            self.btn_iniciar.configure(state="normal")
            if err is None:
                msg = t("drivers_completado", n=paquetes, f=ficheros,
                        t=tamano_legible(bts), d=self.trabajo.destino)
                self.estado.configure(text=t("drivers_completado_t"))
                messagebox.showinfo(t("drivers_titulo"), msg, parent=self)
            elif err == "cancelado":
                self.estado.configure(text=t("cancelado_user"))
            else:
                self.estado.configure(text=err)
                messagebox.showerror(t("drivers_titulo"), t("drivers_error", e=err), parent=self)
        self.after(0, upd)


class DialogoWindows(tk.Toplevel):
    def __init__(self, padre, encontradas):
        super().__init__(padre)
        self.padre = padre
        self.title(t("win_encontradas"))
        self.transient(padre)
        self.grab_set()
        self.geometry("560x360")
        cont = ttk.Frame(self, padding=14)
        cont.pack(fill="both", expand=True)
        ttk.Label(cont, text=t("win_encontradas"),
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
        for letra, version in encontradas:
            fila = ttk.Frame(cont)
            fila.pack(fill="x", pady=4)
            ttk.Label(fila, text=t("win_partition", l=letra, v=version)).pack(side="left")
            ttk.Button(fila, text=t("btn_backup_drivers"),
                       command=lambda l=letra, v=version: DialogoBackupDrivers(self, l, v)
                       ).pack(side="right")
        ttk.Button(cont, text=t("cerrar"), command=self.destroy).pack(side="bottom", pady=(10, 0))


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{NOMBRE_APP} v{VERSION}")
        self.geometry("960x620")
        self.minsize(820, 540)
        self.trabajo = None
        self.dispositivos = []
        self.indice_filas = {}
        self.widgets_i18n = []
        self._construir()
        self._aplicar_idioma()
        self.after(100, self.refrescar_dispositivos)

    def _i18n(self, widget, clave, atrib="text"):
        self.widgets_i18n.append((widget, clave, atrib))

    def _aplicar_idioma(self):
        for widget, clave, atrib in self.widgets_i18n:
            try:
                widget.configure(**{atrib: t(clave)})
            except tk.TclError:
                pass
        try:
            self.arbol.heading("ruta", text=t("col_disp"))
            self.arbol.heading("modelo", text=t("col_modelo"))
            self.arbol.heading("tamano", text=t("col_tam"))
            self.arbol.heading("bus", text=t("col_bus"))
        except Exception:
            pass
        # texto de estado por defecto si está vacío
        if not self.estado.cget("text") or self.estado.cget("text") in (
            TRADUCCIONES["es"]["listo"], TRADUCCIONES["en"]["listo"],
            TRADUCCIONES["es"]["aviso_admin"], TRADUCCIONES["en"]["aviso_admin"],
        ):
            self.estado.configure(text=t("listo") if es_admin() else t("aviso_admin"))

    def _cambiar_idioma(self, evento=None):
        global idioma_actual
        mapa = {"Español": "es", "English": "en"}
        seleccion = self.cmb_idioma.get()
        idioma_actual = mapa.get(seleccion, "en")
        self._aplicar_idioma()

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
        lbl_sub = ttk.Label(cab, font=("Segoe UI", 10), foreground="#666")
        lbl_sub.pack(side="left")
        self._i18n(lbl_sub, "subtitulo")

        self.cmb_idioma = ttk.Combobox(cab, values=["Español", "English"],
                                       state="readonly", width=10)
        self.cmb_idioma.set("Español")
        self.cmb_idioma.bind("<<ComboboxSelected>>", self._cambiar_idioma)
        self.cmb_idioma.pack(side="right")
        lbl_idi = ttk.Label(cab)
        lbl_idi.pack(side="right", padx=(0, 6))
        self._i18n(lbl_idi, "idioma")

        sub = ttk.Frame(self, padding=(14, 0, 14, 0))
        sub.pack(fill="x")
        b_kofi = ttk.Button(sub, command=lambda: webbrowser.open(URL_KOFI))
        b_kofi.pack(side="right")
        self._i18n(b_kofi, "kofi")
        b_gh = ttk.Button(sub, command=lambda: webbrowser.open(URL_REPO))
        b_gh.pack(side="right", padx=6)
        self._i18n(b_gh, "github")
        b_win = ttk.Button(sub, command=self.buscar_windows)
        b_win.pack(side="right", padx=6)
        self._i18n(b_win, "buscar_windows")
        b_ref = ttk.Button(sub, command=self.refrescar_dispositivos)
        b_ref.pack(side="right", padx=6)
        self._i18n(b_ref, "refrescar")

        ppal = ttk.Frame(self, padding=(14, 8, 14, 14))
        ppal.pack(fill="both", expand=True)

        cols = ("ruta", "modelo", "tamano", "bus")
        self.arbol = ttk.Treeview(ppal, columns=cols, show="tree headings", height=12)
        self.arbol.column("#0", width=24, stretch=False)
        for c, w, anc in (("ruta", 220, "w"), ("modelo", 320, "w"),
                          ("tamano", 120, "e"), ("bus", 120, "w")):
            self.arbol.column(c, width=w, anchor=anc)
        self.arbol.pack(fill="both", expand=True, pady=(0, 10))

        self.ops = ttk.LabelFrame(ppal, padding=10)
        self.ops.pack(fill="x", pady=(0, 8))
        self._i18n(self.ops, "opciones", atrib="text")
        lbl_fmt = ttk.Label(self.ops)
        lbl_fmt.pack(side="left")
        self._i18n(lbl_fmt, "formato")
        self.formato = tk.StringVar(value="gz")
        for etiqueta, val in (("img.gz", "gz"), ("img.zip", "zip"), ("img.tar.gz", "tar.gz")):
            ttk.Radiobutton(self.ops, text=etiqueta, variable=self.formato, value=val).pack(side="left", padx=6)
        self.rb_raw = ttk.Radiobutton(self.ops, variable=self.formato, value="raw")
        self.rb_raw.pack(side="left", padx=6)
        self._i18n(self.rb_raw, "formato_sin_comp")
        self.calc_hash = tk.BooleanVar(value=True)
        self.chk_hash = ttk.Checkbutton(self.ops, variable=self.calc_hash)
        self.chk_hash.pack(side="left", padx=(20, 0))
        self._i18n(self.chk_hash, "calc_hash")

        acc = ttk.Frame(ppal)
        acc.pack(fill="x", pady=(0, 8))
        self.btn_crear = ttk.Button(acc, command=self.iniciar_backup)
        self.btn_crear.pack(side="right")
        self._i18n(self.btn_crear, "crear_backup")
        self.btn_verificar = ttk.Button(acc, command=self.iniciar_verificacion)
        self.btn_verificar.pack(side="right", padx=6)
        self._i18n(self.btn_verificar, "verificar_backup")
        self.btn_cancelar = ttk.Button(acc, command=self.cancelar, state="disabled")
        self.btn_cancelar.pack(side="right", padx=6)
        self._i18n(self.btn_cancelar, "cancelar")

        self.barra = ttk.Progressbar(ppal, mode="determinate", maximum=1000)
        self.barra.pack(fill="x")
        self.estado = ttk.Label(ppal, anchor="w")
        self.estado.pack(fill="x", pady=(8, 0))

    def refrescar_dispositivos(self):
        for hijo in self.arbol.get_children():
            self.arbol.delete(hijo)
        self.indice_filas.clear()
        try:
            self.dispositivos = listar_dispositivos()
        except Exception as e:
            messagebox.showerror(NOMBRE_APP, t("err_listar", e=e))
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
        self.estado.configure(text=t("n_discos", n=len(self.dispositivos)))

    def buscar_windows(self):
        self.estado.configure(text=t("buscando_win"))
        self.update_idletasks()
        encontradas = []
        for d in self.dispositivos:
            for p in d.get("particiones", []):
                letra = p.get("letra")
                if not letra:
                    continue
                version = detectar_windows_en_particion(letra)
                if version:
                    encontradas.append((letra, version))
        if not encontradas:
            messagebox.showinfo(NOMBRE_APP, t("win_no_encontradas"))
            self.estado.configure(text=t("listo"))
            return
        self.estado.configure(text=t("listo"))
        DialogoWindows(self, encontradas)

    def _seleccionado(self):
        sel = self.arbol.selection()
        if not sel:
            return None
        return self.indice_filas.get(sel[0])

    def iniciar_backup(self):
        if not es_admin():
            messagebox.showerror(NOMBRE_APP, t("err_admin"))
            return
        d = self._seleccionado()
        if not d:
            messagebox.showinfo(NOMBRE_APP, t("sel_disp"))
            return
        if not d.get("tamano"):
            if not messagebox.askyesno(NOMBRE_APP, t("tam_desconocido")):
                return
        f = self.formato.get()
        ext = {"gz": ".img.gz", "zip": ".img.zip", "tar.gz": ".img.tar.gz", "raw": ".img"}[f]
        nombre_seguro = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in (d["modelo"] or "device")
        )[:40] or "device"
        sufijo = "_part" if d.get("tipo") == "particion" else ""
        por_defecto = f"tkz_backup_{nombre_seguro}{sufijo}{ext}"
        salida = filedialog.asksaveasfilename(
            title=t("guardar_como"),
            defaultextension=ext,
            initialfile=por_defecto,
            filetypes=[("TKZ Backup", "*" + ext), ("*.*", "*.*")],
        )
        if not salida:
            return
        confirmar = messagebox.askyesno(
            NOMBRE_APP,
            t("confirmar_backup", r=d["ruta"], m=d["modelo"], t=tamano_legible(d["tamano"]), o=salida),
        )
        if not confirmar:
            return
        self.barra["value"] = 0
        self.btn_crear.configure(state="disabled")
        self.btn_verificar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.estado.configure(text=t("iniciando", r=d["ruta"]))
        self.trabajo = TrabajadorBackup(
            d["ruta"], d["tamano"], salida, f,
            self.calc_hash.get(), self._cb_progreso, self._cb_fin_backup,
        )
        self.trabajo.start()

    def iniciar_verificacion(self):
        ruta = filedialog.askopenfilename(
            title=t("sel_verificar"),
            filetypes=[("TKZ Backup", "*.gz *.zip *.tgz *.img"), ("*.*", "*.*")],
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
            if messagebox.askyesno(NOMBRE_APP, t("no_sidecar")):
                dlg = tk.Toplevel(self)
                dlg.title("SHA-256")
                dlg.transient(self)
                dlg.grab_set()
                tk.Label(dlg, text=t("hash_label")).pack(padx=12, pady=(12, 4))
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
        self.estado.configure(text=t("verificando", f=os.path.basename(ruta)))
        self.trabajo = VerificadorBackup(ruta, esperado, self._cb_progreso, self._cb_fin_verif)
        self.trabajo.start()

    def cancelar(self):
        if self.trabajo:
            self.trabajo.cancelar()
            self.estado.configure(text=t("cancelando"))

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
                msg = t("completado_msg")
                if hash_hex:
                    msg += t("sha_guardado", h=hash_hex)
                self.estado.configure(text=t("estado_completado"))
                messagebox.showinfo(NOMBRE_APP, msg)
            elif err == "cancelado":
                self.estado.configure(text=t("cancelado_user"))
            else:
                self.estado.configure(text=f"Error: {err}")
                messagebox.showerror(NOMBRE_APP, err)
        self.after(0, upd)

    def _cb_fin_verif(self, err, hex_calc, coincide):
        def upd():
            self._resetear_botones()
            if err == "cancelado":
                self.estado.configure(text=t("verif_cancelada"))
                return
            if err is not None:
                self.estado.configure(text=f"Error: {err}")
                messagebox.showerror(NOMBRE_APP, err)
                return
            self.barra["value"] = 1000
            if coincide is None:
                self.estado.configure(text=t("hash_calculado"))
                messagebox.showinfo(NOMBRE_APP, t("hash_msg", h=hex_calc))
            elif coincide:
                self.estado.configure(text=t("integ_ok"))
                messagebox.showinfo(NOMBRE_APP, t("integ_ok_msg", h=hex_calc))
            else:
                self.estado.configure(text=t("integ_fail"))
                messagebox.showerror(NOMBRE_APP, t("integ_fail_msg", h=hex_calc))
        self.after(0, upd)


def principal():
    if platform.system() == "Windows" and not es_admin():
        relanzar_como_admin()
        return
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    principal()
