# Meshroom Video Plugin

Plugin para Meshroom que permite procesar videos y extraer frames para reconstrucción 3D. Extrae fotogramas de videos mientras preserva metadatos GPS/EXIF para una reconstrucción más precisa.

## Características

- Extracción de frames de video con FFmpeg o OpenCV
- Preservación mejorada de metadatos GPS/EXIF para cada frame
- Transferencia de datos de telemetría de drones (gimbal, velocidad, altitud)
- Timestamping preciso de cada fotograma basado en su posición en el video
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
--keep-metadata, -k  Preservar y mejorar metadatos GPS/EXIF y telemetría
--quality, -q       Calidad del procesamiento ('low', 'medium', 'high')
--start, -s         Tiempo de inicio para la extracción (formato: HH:MM:SS)
--duration, -d      Duración del segmento a extraer (formato: HH:MM:SS)
--detect-blur, -b   Activar detección de fotogramas borrosos
--blur-threshold, -t Umbral para detección de blur (default: 100.0)
--meshroom-bin, -m  Ruta al ejecutable de Meshroom
```

## Ejemplos de Uso

### Extracción básica

```bash
meshroom-video video.mp4
```

### Extracción con metadatos avanzados y rotación

```bash
meshroom-video video.mp4 --output ./frames --rotate 90 --keep-metadata --verbose
```

### Extracción de vídeos de drones con preservación de telemetría

```bash
meshroom-video DJI_0001.mp4 --keep-metadata --rotate auto --verbose
```

### Extraer frames de alta calidad evitando fotogramas borrosos

```bash
meshroom-video video.mp4 --detect-blur --blur-threshold 150 --frame-interval 30
```

### Extraer frames desde un tiempo específico

```bash
meshroom-video video.mp4 --start 00:02:00 --duration 00:00:30
```

### Extraer frames cada segundo para vídeos con movimiento lento

```bash
meshroom-video slowmotion.mp4 --frame-interval 30 --keep-metadata
```

### Procesamiento de vídeo 4K (menor cantidad de frames)

```bash
meshroom-video 4K_video.mp4 --frame-interval 60 --quality high --keep-metadata
```

### Extracción para objetos pequeños con gran detalle

```bash
meshroom-video closeup.mp4 --frame-interval 10 --detect-blur --blur-threshold 200
```

### Vídeos de drones con visión cenital para mapeo

```bash
meshroom-video drone_map.mp4 --keep-metadata --frame-interval 20 --quality high
```

## Integración con Meshroom

Los frames extraídos se procesan automáticamente con Meshroom para generar el modelo 3D. Si se ha utilizado la opción `--keep-metadata`, Meshroom podrá aprovechar la información GPS/EXIF y telemetría para mejorar la reconstrucción.

### Recomendaciones para configuración de nodos de Meshroom

Para obtener mejores resultados con fotogramas extraídos de vídeos, se recomienda ajustar ciertos parámetros en Meshroom:

#### CameraInit

- **viewIdMethod**: METADATA (aprovecha los datos de timestamp y secuencia)
- **verboseLevel**: INFO (útil para verificar que los metadatos se leen correctamente)
- Al trabajar con videos de drones con GPS:
  - Activar **Landmark Constraints** para aprovechar la geolocalización
  - **positionConstraints**: SOFT (para drones de consumo con GPS menos preciso)

#### FeatureExtraction

- **describer/quality**: NORMAL para vídeos estándar, HIGH para vídeos 4K
- **describer/contrastFiltering**: GridSort (mejor distribución de features)
- **describer/gridFiltering**: TRUE (mejora el emparejamiento en vídeos)
- **forceCpuExtraction**: True para sets de datos grandes

#### ImageMatching

- **tree**: VOCAB_TREE (más eficiente para secuencias de vídeo)
- **weights**: WORD_FREQUENCY (mejor para frames consecutivos)
- **minNbImages**: 50 (ajustar según cantidad de frames)

#### FeatureMatching

- **guidedMatching**: TRUE (mejora resultados en secuencias de vídeo)
- **photometricMatchingMethod**: ANN_L2
- **geometricEstimator**: ACRANSAC
- **geometricFilterType**: FUNDAMENTAL_MATRIX

#### StructureFromMotion

- **minInputTrackLength**: 2 (óptimo para vídeos con frames consecutivos)
- **lockScenePreviouslyReconstructed**: False
- **lockAllIntrinsics**: True (para vídeos donde la cámara no cambia)
- **initialPairA** y **initialPairB**: Dejar vacío para que use los metadatos

#### PrepareDenseScene

- **imagesSizeRatio**: 0.5 para vídeos estándar, 1 para tomas detalladas

#### DepthMap

- **downscale**: 2 para mejor rendimiento, 1 para máximo detalle
- **minViewAngle**: 1.0 (mejor para frames de video secuenciales)
- **maxViewAngle**: 40.0
- **sgmGammaC**: 5.5 (incrementar para escenas con poca textura)

#### Meshing

- **maxInputPoints**: 500000 (incrementar para escenas complejas)
- **maxPoints**: 200000
- **minFilteredTriangleArea**: 0.5 (reducir para preservar detalles)

#### Texturing

- **unwrapMethod**: BASIC (más rápido) o ABF (mejor calidad)
- **padding**: 5 (aumentar si hay artefactos en texturas)
- **downscale**: 1 para máxima calidad, 2 para mejor rendimiento

## Metadatos Mejorados

En la versión 0.2.0 se ha mejorado significativamente la transferencia de metadatos de video a fotogramas:

- **Datos GPS**: Coordenadas precisas con referencias de dirección
- **Telemetría de drones**: Ángulos de gimbal, velocidad, altitud, etc.
- **Timestamps precisos**: Cada fotograma mantiene su posición temporal exacta
- **Información de sensor**: Cálculos automáticos de dimensiones del sensor
- **Compatibilidad con fotogrametría**: Metadatos específicos para mejor reconstrucción 3D

Para más detalles, consulta la [documentación de metadatos](docs/metadata_improvements.md).

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