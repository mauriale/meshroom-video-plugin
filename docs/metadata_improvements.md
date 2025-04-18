# Mejoras en la Transferencia de Metadatos de Video a Fotogramas

Este documento describe las mejoras implementadas en la versión 0.2.0 del plugin para transferir más metadatos de video a los fotogramas extraídos.

## Cambios Principales

### 1. Extracción Mejorada de Metadatos del Video

- Mejor detección y extracción de metadatos XMP específicos para drones
- Soporte ampliado para datos de telemetría (gimbal, altitud, velocidad, etc.)
- Procesamiento de metadatos de múltiples fabricantes de drones
- Cálculo y almacenamiento de información del sensor
- Detección de rotación automática a partir de metadatos del video

### 2. Transferencia Mejorada de Metadatos a Fotogramas

- Timestamps precisos por fotograma basados en la posición en el video
- Transferencia de datos de gimbal como metadatos XMP
- Inclusión de datos de telemetría de drones
- Mejor aplicación de metadatos EXIF estándar
- Almacenamiento de información del sensor como metadatos

### 3. Metadatos Específicos para Fotogrametría

- Inclusión de más datos relevantes para la reconstrucción 3D
- Etiquetas XMP específicas para software de fotogrametría
- Preservación de ángulos de gimbal importantes para la orientación inicial
- Metadatos de GPS mejorados para geolocalización precisa

## Implementación Técnica

### Procesamiento de Metadatos en el Video

El plugin ahora utiliza un enfoque en capas para la extracción de metadatos:

1. **Metadatos XMP específicos**: Extraídos utilizando ExifTool con parámetros especiales para obtener datos XMP estructurados
2. **Metadatos EXIF generales**: Extraídos con ExifTool para obtener información estándar de cámara y GPS
3. **Metadatos de FFmpeg**: Obtenidos mediante el análisis de streams de video para detectar rotación y parámetros técnicos
4. **Valores por defecto inteligentes**: Calculados basándose en características detectadas del video

### Extracción de Datos de Drones

Para videos de drones, el plugin ahora:

1. Busca metadatos específicos del fabricante en diferentes formatos (DJI, Parrot, etc.)
2. Extrae información de gimbal (pitch/roll/yaw) útil para la orientación de cámaras
3. Obtiene datos de vuelo como altitud, velocidad y distancia
4. Preserva coordenadas GPS con referencias de dirección y altitud
5. Detecta automáticamente la rotación del video y la aplica correctamente

### Timestamp Preciso por Fotograma

Una mejora significativa es el cálculo preciso del timestamp para cada fotograma:

```python
# Snippet del código que aplica timestamps precisos
base_time_str = video_metadata['Exif.Image.DateTime']
base_time = datetime.strptime(base_time_str, '%Y:%m:%d %H:%M:%S')
# Añadir el timestamp del fotograma (segundos desde el inicio)
frame_datetime = base_time + timedelta(seconds=timestamp)
frame_time = frame_datetime.strftime('%Y:%m:%d %H:%M:%S')
```

Esto permite que cada fotograma mantenga su posición temporal exacta en el video, lo que es crucial para la secuenciación correcta en Meshroom.

## Beneficios para la Reconstrucción 3D

Estas mejoras ofrecen varios beneficios para el proceso de fotogrametría:

1. **Mejor calibración de cámara**: Los datos precisos de distancia focal y dimensiones del sensor mejoran la calibración.

2. **Posicionamiento más preciso**: Los datos de GPS y orientación de gimbal permiten un mejor posicionamiento inicial.

3. **Mejor escala y orientación**: La información adicional de telemetría ayuda a establecer la escala correcta del modelo.

4. **Compatibilidad con flujos de trabajo avanzados**: Los metadatos enriquecidos permiten el procesamiento avanzado en Meshroom y otros software.

5. **Secuenciación correcta**: Los timestamps precisos aseguran que Meshroom entienda el orden correcto de los fotogramas.

## Ejemplos de Metadatos Mejorados

### Datos de Gimbal

```
Xmp.drone.GimbalPitchDegree: -30.2
Xmp.drone.GimbalRollDegree: 0.1
Xmp.drone.GimbalYawDegree: 45.5
```

### Datos de Vuelo

```
Xmp.drone.FlightSpeedMps: 4.2
Xmp.drone.RelativeAltitude: 42.5
Xmp.drone.FlightYawDegree: 285.3
Xmp.drone.DistanceFromHome: 128.7
```

### Timestamps Precisos

```
Exif.Image.DateTime: 2025:04:12 11:57:32
Exif.Photo.DateTimeOriginal: 2025:04:12 11:57:47
Exif.Photo.UserComment: Frame timestamp: 15.320s
Xmp.video.FrameTimeSeconds: 15.320
```

### Información del Sensor y Cámara

```
Exif.Photo.FocalLength: 24/1
Exif.Photo.FocalLengthIn35mmFilm: 24
Exif.Photo.FNumber: 28/10
Sensor dimensions: 6.32mm x 4.73mm
Xmp.exif.FocalPlaneXResolution: 632
Xmp.exif.FocalPlaneYResolution: 473
Xmp.exif.FocalPlaneResolutionUnit: 3
```

### Datos GPS

```
Exif.GPSInfo.GPSLatitudeRef: N
Exif.GPSInfo.GPSLatitude: 43/1 31/1 84/100
Exif.GPSInfo.GPSLongitudeRef: E
Exif.GPSInfo.GPSLongitude: 7/1 3/1 432/100
Exif.GPSInfo.GPSAltitudeRef: 0
Exif.GPSInfo.GPSAltitude: 42500/1000
```

## Ejemplos de Uso

### Extracción Básica con Metadatos

```bash
meshroom-video video.mp4 --keep-metadata --verbose
```

### Vídeos de Drones con Rotación Automática

```bash
meshroom-video DJI_0001.mp4 --keep-metadata --rotate auto --verbose
```

### Vídeos de Drones para Mapeo

```bash
meshroom-video drone_map.mp4 --keep-metadata --frame-interval 20 --quality high
```

### Videos 4K con Alta Calidad

```bash
meshroom-video 4K_video.mp4 --frame-interval 60 --quality high --keep-metadata
```

## Visualización de Metadatos en Fotogramas

Para verificar que los metadatos se han transferido correctamente, puedes usar ExifTool en los fotogramas extraídos:

```bash
exiftool -G -a -u frame_000001.jpg
```

Esto mostrará todos los metadatos, incluyendo los grupos específicos de drones y video.

## Compatibilidad

- Las mejoras son compatibles con todas las versiones de pyexiv2
- Se ha probado con videos de drones DJI, pero debería funcionar con otros fabricantes
- Se admiten formatos MP4, MOV y AVI con metadatos
- Los metadatos adicionales son ignorados por software que no los entiende
- Funciona con Meshroom 2021.1.0 y versiones posteriores

## Solución de Problemas

### Timestamps Precisos

Si encuentras el error "Could not calculate precise frame timestamp", asegúrate de que la versión del plugin sea 0.2.0 o superior, donde se ha corregido la importación del módulo `timedelta`.

### Metadatos de Drones

Para obtener el máximo de metadatos en videos de drones, asegúrate de tener instalado ExifTool (versión 12.0 o superior recomendada).

### Rotación Automática

La rotación automática funciona mejor con videos que contienen metadatos de rotación. Si no se detecta automáticamente, puedes especificar la rotación manualmente con `--rotate 90`, etc.

## Contribuciones Futuras

Áreas de mejora para futuras versiones:

1. Soporte para más formatos de metadatos específicos de drones
2. Extracción de datos de IMU y acelerómetro
3. Análisis de secuencias de movimiento para mejorar la estimación de la trayectoria
4. Exportación directa de metadatos a formatos específicos de fotogrametría