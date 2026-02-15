# Utilise une image Python officielle légère
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

# Installation de dépendances système si nécessaire (ex: pour Folium/Pandas)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie le fichier requirements.txt pour installer les libs au démarrage
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp