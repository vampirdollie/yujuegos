# Usa Python 3.11 estable
FROM python:3.11-slim

# Establece directorio de trabajo
WORKDIR /app

# Copia dependencias e instálalas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Comando de inicio
CMD ["python", "main.py"]
