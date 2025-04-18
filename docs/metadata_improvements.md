# Mejoras en la Transferencia de Metadatos de Video a Fotogramas

Este documento describe las mejoras implementadas en la versión 0.2.0 del plugin para transferir más metadatos de video a los fotogramas extraídos.

## Cambios Principales

### 1. Extracción Mejorada de Metadatos del Video

- Mejor detección y extracción de metadatos XMP específicos para drones
- Soporte ampliado para datos de telemetría (gimbal, altitud, velocidad, etc.)
- Procesamiento de metadatos de múltiples fabricantes de drones
- Cálculo y almacenamiento de información del sensor

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

## Beneficios para la Reconstrucción 3D

Estas mejoras ofrecen varios beneficios para el proceso de fotogrametría:

1. **Mejor calibración de cámara**: Los datos precisos de distancia focal y dimensiones del sensor mejoran la calibración.

2. **Posicionamiento más preciso**: Los datos de GPS y orientación de gimbal permiten un mejor posicionamiento inicial.

3. **Mejor escala y orientación**: La información adicional de telemetría ayuda a establecer la escala correcta del modelo.

4. **Compatibilidad con flujos de trabajo avanzados**: Los metadatos enriquecidos permiten el procesamiento avanzado en Meshroom y otros software.

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
```

### Timestamps Precisos

```
Exif.Photo.UserComment: Frame timestamp: 15.320s
Xmp.video.FrameTimeSeconds: 15.320
```

### Información del Sensor

```
Sensor dimensions: 6.32mm x 4.73mm
Xmp.exif.FocalPlaneXResolution: 632
Xmp.exif.FocalPlaneYResolution: 473
Xmp.exif.FocalPlaneResolutionUnit: 3
```

## Uso

Estas mejoras están automáticamente activadas cuando se usa la opción `--keep-metadata`:

```bash
meshroom-video video.mp4 --keep-metadata --verbose
```

Para videos de drones con rotación, se recomienda el modo auto:

```bash
meshroom-video DJI_0001.mp4 --keep-metadata --rotate auto --verbose
```

## Compatibilidad

- Las mejoras son compatibles con todas las versiones de pyexiv2
- Se ha probado con videos de drones DJI, pero debería funcionar con otros fabricantes
- Los metadatos adicionales son ignorados por software que no los entiende