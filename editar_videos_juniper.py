import os
import time
import numpy as np
import shutil
from datetime import datetime
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from moviepy.video.fx.resize import resize
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.audio.fx.all import audio_normalize
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Rutas
carpeta_detectados = "videos_virales_detectados"
carpeta_editados = "videos_editados"
logo_path = "juniper_logo.png"
duracion_maxima = 60  # segundos

# Autenticación persistente con Google Drive
gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")
if gauth.credentials is None:
    gauth.LocalWebserverAuth()
    gauth.SaveCredentialsFile("mycreds.txt")
elif gauth.access_token_expired:
    gauth.Refresh()
    gauth.SaveCredentialsFile("mycreds.txt")
else:
    gauth.Authorize()

drive = GoogleDrive(gauth)

def elegir_mejor_fragmento(video):
    duracion = int(video.duration)
    mejor_puntaje = 0
    mejor_inicio = 0

    for i in range(0, duracion - duracion_maxima + 1, 5):
        subclip = video.subclip(i, i + duracion_maxima)

        try:
            volumen_arr = subclip.audio.to_soundarray(fps=22000)
            volumen = abs(volumen_arr).mean()
        except Exception:
            volumen = 0

        try:
            frames = list(subclip.iter_frames(fps=1))
            movimiento = sum(np.abs(frames[j] - frames[j - 1]).sum() for j in range(1, len(frames)))
        except Exception:
            movimiento = 0

        puntaje = volumen * 0.6 + movimiento * 0.4

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_inicio = i

    return mejor_inicio, mejor_inicio + duracion_maxima

def adaptar_a_vertical(clip):
    target_ratio = 9 / 16
    clip_ratio = clip.w / clip.h

    if clip_ratio > target_ratio:
        new_width = int(clip.h * target_ratio)
        x1 = (clip.w - new_width) // 2
        x2 = x1 + new_width
        clip = clip.crop(x1=x1, x2=x2)

    return resize(clip, height=1920)

def calcular_logo(clip):
    ratio = clip.w / clip.h
    if 0.55 < ratio < 0.65:
        scale = 0.08
    else:
        scale = 0.13

    logo = (ImageClip(logo_path)
            .set_duration(clip.duration)
            .resize(height=int(clip.h * scale))
            .margin(right=30, bottom=100, opacity=0)
            .set_pos(lambda t: ("right", int(clip.h * 0.92 + np.sin(t) * 3))))

    return logo

def procesar_video(ruta_video):
    try:
        nombre_archivo = os.path.basename(ruta_video)
        print(f"Procesando: {nombre_archivo}")

        with VideoFileClip(ruta_video) as clip:
            if clip.duration > duracion_maxima:
                inicio, fin = elegir_mejor_fragmento(clip)
                print(f"Mejores 60s detectados entre el segundo {inicio} y {fin}")
                clip = clip.subclip(inicio, fin)
            else:
                print("Duración inferior a 60s, no se recorta.")

            # Zoom leve
            clip = clip.fx(resize, 1.05)

            # Adaptar formato vertical
            clip = adaptar_a_vertical(clip)

            # Normalizar audio
            if clip.audio:
                clip = clip.set_audio(audio_normalize(clip.audio))

            # Fade in / fade out
            clip = fadein(clip, 1)
            clip = fadeout(clip, 1)

            # Logo
            logo = calcular_logo(clip)

            final = CompositeVideoClip([clip, logo])

            if not os.path.exists(carpeta_editados):
                os.makedirs(carpeta_editados)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_salida = f"edit_{timestamp}_{nombre_archivo}"
            salida = os.path.join(carpeta_editados, nombre_salida)

            final.write_videofile(salida, codec="libx264", audio_codec="aac", verbose=False, logger=None)

            archivo = drive.CreateFile({'title': nombre_salida})
            archivo.SetContentFile(salida)
            archivo.Upload()
            print("Subido a Drive:", archivo['title'])

            final.close()
            logo.close()

        time.sleep(1)
        os.remove(ruta_video)

    except Exception as e:
        print(f"Error al procesar {ruta_video}: {e}")

def main():
    if not os.path.exists(carpeta_detectados):
        print(f"No se encontró la carpeta '{carpeta_detectados}'")
        return

    archivos = os.listdir(carpeta_detectados)
    for archivo in archivos:
        if archivo.endswith((".mp4", ".mov", ".avi")):
            ruta = os.path.join(carpeta_detectados, archivo)
            procesar_video(ruta)

if __name__ == "__main__":
    main()
