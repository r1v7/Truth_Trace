FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

# WeasyPrint renders the PDF reports; it needs Pango/Cairo and a font with Arabic
# coverage. A headless browser would work too, but would have to be downloaded at
# build time, which the offline requirement rules out.
RUN apt-get update && apt-get install -y --no-install-recommends         libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0         fonts-dejavu-core fonts-noto-core     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
