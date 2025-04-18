# Meshroom Video Plugin

Plugin para Meshroom que permite procesar videos y extraer frames para reconstrucción 3D. Extrae fotogramas de videos mientras preserva metadatos GPS/EXIF para una reconstrucción más precisa.

## Características

- Extracción de frames de video con FFmpeg o OpenCV
- Preservación de metadatos GPS/EXIF para cada frame
- Detección de fotogramas borrosos (blur) para mejorar la calidad
- Rotación automática o manual (0, 90, 180, 270 grados)
- Extracción desde tiempos específicos del video
- Modo verbose para seguimiento detallado del proceso

## Requisitos

- [Meshroom](https://github.com/alicevision/meshroom)
- [FFmpeg](https://ffmpeg.org/) (opcional pero recomendado)
- [ExifTool](https://exiftool.org/) (opcional para extracción de metadatos)
- Python 3.6+
- OpenCV (se instala automáticamente)

## Instalación

```bash
pip install git+https://github.com/mauriale/meshroom-video-plugin.git
```

O clonando el repositorio:

```bash
git clone https://github.com/mauriale/meshroom-video-plugin.git
cd meshroom-video-plugin
pip install -e .
```

## Uso

### Línea de comandos básica

```bash
meshroom-video video.mp4 --output ./modelo_3d
```

### Opciones disponibles

```
--output, -o        Directorio de salida para los frames extraídos
--frame-interval, -f Frames por segundo a extraer (por defecto: 15)
--rotate, -r        Rotar frames (opciones: 0, 90, 180, 270, 'auto')
--verbose, -v       Mostrar información detallada sobre el progreso
--extract-metadata, -e Extraer metadatos GPS/EXIF y aplicarlos a los frames
--quality, -q       Calidad del procesamiento ('low', 'medium', 'high')
--start, -s         Tiempo de inicio para la extracción (formato: HH:MM:SS)
--duration, -d      Duración del segmento a extraer (formato: HH:MM:SS)
--detect-blur, -b   Activar detección de fotogramas borrosos
--blur-threshold, -t Umbral para detección de blur (default: 100.0)
--meshroom-bin, -m  Ruta al ejecutable de Meshroom
```

## Ejemplos

### Extracción básica

```bash
meshroom-video video.mp4
```

### Extracción con metadatos y rotación

```bash
meshroom-video video.mp4 --output ./frames --rotate 90 --extract-metadata --verbose
```

### Extraer frames de alta calidad evitando fotogramas borrosos

```bash
meshroom-video video.mp4 --detect-blur --blur-threshold 150 --frame-interval 30
```

### Extraer frames desde un tiempo específico

```bash
meshroom-video video.mp4 --start 00:02:00 --duration 00:00:30
```

## Integración con Meshroom

Los frames extraídos se procesan automáticamente con Meshroom para generar el modelo 3D. Si se ha utilizado la opción `--extract-metadata`, Meshroom podrá aprovechar la información GPS/EXIF para mejorar la reconstrucción.

## Flujo de Proceso

1. **Análisis de Video**: El plugin analiza el archivo de video para determinar información como resolución y rotación.
2. **Extracción de Fotogramas**: Se extraen fotogramas utilizando FFmpeg (preferido) o OpenCV, preservando la calidad visual.
3. **Detección de Blur**: Si está activado, se analizan los fotogramas para evitar usar imágenes borrosas.
4. **Procesamiento de Metadatos**: 
   - Se extraen datos GPS, EXIF y timestamps del video
   - Se aplican estos metadatos a cada fotograma extraído
5. **Procesamiento en Meshroom**: El plugin llama a Meshroom con los fotogramas preparados
6. **Generación del Modelo 3D**: Meshroom completa el procesamiento de fotogrametría
7. **Limpieza**: Se eliminan los archivos temporales después del procesamiento

## Solución de Problemas

Si encuentras errores:

1. Asegúrate de que FFmpeg y ExifTool estén instalados y en tu PATH
2. Verifica que Meshroom esté instalado correctamente
3. Para videos de alta resolución, considera usar `--frame-interval` más alto
4. Con la opción `--verbose` puedes obtener más información sobre los errores

## Contribuir

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir cambios importantes antes de enviar un pull request.

## Licencia

MIT
