# TKZ Backup

Herramienta de backup de **discos y particiones** con compresión *on-the-fly* (sin archivo intermedio), interfaz gráfica sencilla y verificación de integridad por SHA-256.

Pensada principalmente para crear imágenes de **dispositivos USB** desde Windows, pero el código es multiplataforma (Windows / Linux / macOS).

## Características

- GUI nativa (Tkinter / ttk).
- Detección automática de discos físicos y sus particiones.
- Compresión en streaming: el dispositivo se lee y se comprime al mismo tiempo, sin ocupar espacio extra para una imagen intermedia.
- Formatos soportados: `img.gz`, `img.zip`, `img.tar.gz` o `img` (sin comprimir).
- Lectura raw a 16 MB con `FILE_FLAG_NO_BUFFERING` + arquitectura productor/consumidor en hilos (lectura de disco y compresión en paralelo).
- Cálculo de **SHA-256** durante el backup y sidecar `.sha256` para verificar después.
- Botón **Verificar backup** que descomprime en streaming y compara hashes.
- En Windows se solicita elevación UAC automáticamente (manifiesto `requireAdministrator`).

## Uso

1. Descarga el `TKZ Backup.exe` desde *Releases* (Windows).
2. Doble clic → acepta el UAC.
3. Selecciona el disco o la partición.
4. Elige formato (recomendado `img.gz`).
5. **Crear backup…**
6. Cuando termine, conserva el archivo `.sha256` junto al backup y úsalo con **Verificar backup…**.

## Compilar desde código

Requiere Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --uac-admin --name "TKZ Backup" tkz_backup.py
```

En Linux/macOS basta con ejecutar `sudo python tkz_backup.py` (o compilar con PyInstaller en esa plataforma).

## Apoyo

Si te resulta útil, puedes invitarme a un café en [Ko-fi](https://ko-fi.com/trankten) ❤

## Licencia

MIT
