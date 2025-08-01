# Utilisation d'une image Python officielle sur Debian stable pour la compatibilité avec Playwright
FROM python:3.9-bullseye

# Configuration des variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installation des dépendances système requises pour Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dépendances pour Playwright
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libatspi2.0-0 libwayland-client0 \
    # Packages supplémentaires pour éviter les problèmes avec les navigateurs
    fonts-noto-color-emoji fonts-freefont-ttf \
    # Packages pour la construction de certains paquets Python
    build-essential libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Mise en place de l'environnement Python
RUN pip install --upgrade pip setuptools wheel

# Copie des fichiers nécessaires en respectant l'ordre pour l'installation editable
COPY pyproject.toml README.md ./
COPY core/ ./core/
COPY scripts/ ./scripts/

# Installation des dépendances Python incluant crawl4ai
RUN pip install -e .

# Installation de Playwright et téléchargement des navigateurs
RUN pip install playwright && \
    playwright install --with-deps chromium

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "core.app:app", "--host", "0.0.0.0", "--port", "8000"]
