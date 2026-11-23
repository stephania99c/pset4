# Imagen de los scripts de Python del proyecto: simulacion, monitoreo,
# reentrenamiento y tablero. El codigo no se copia: Kestra y el tablero montan
# la carpeta del proyecto, asi que un cambio en el codigo no obliga a reconstruirla.
FROM python:3.12-slim

WORKDIR /proyecto

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt