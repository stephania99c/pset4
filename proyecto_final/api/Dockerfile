FROM python:3.12-slim

WORKDIR /app

# Mismas versiones con las que se entreno el modelo en el PSet 3
RUN pip install --no-cache-dir \
    "mlflow==2.17.2" "scikit-learn==1.5.2" "sqlalchemy<2.1" \
    pandas fastapi uvicorn

COPY esquemas.py main.py ./

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]