#!/usr/bin/env python3
"""
Script d'installation du projet Syntinel avec uv

Ce script automatise la création d'un environnement de développement pour Syntinel
en utilisant uv, un gestionnaire ultra-rapide de dépendances et d'environnements virtuels.

Utilisation:
    python scripts/setup_dev.py
"""

import os
import sys
import subprocess
import platform
import shutil


def run_command(cmd, description=None, exit_on_error=True):
    """Exécute une commande shell et affiche le résultat"""
    if description:
        print(f"\n[*] {description}...")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True,
                               capture_output=True)
        print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        print(f"   {e.stderr.strip()}")
        if exit_on_error:
            sys.exit(1)
        return False


def check_uv_installed():
    """Vérifie si uv est installé et l'installe si nécessaire"""
    if shutil.which("uv"):
        print("✅ uv est déjà installé")
        return True
    
    print("🔍 uv n'est pas installé. Installation en cours...")
    
    if platform.system() == "Windows":
        print("Sur Windows, veuillez installer uv manuellement:")
        print("https://github.com/astral-sh/uv#installation")
        sys.exit(1)
    else:
        install_cmd = "curl -sSf https://install.astronomer.io/uv | bash"
        return run_command(install_cmd, "Installation de uv")


def check_direnv_installed():
    """Vérifie si direnv est installé et suggère l'installation"""
    if shutil.which("direnv"):
        print("✅ direnv est déjà installé")
        return True
    
    print("🔍 direnv n'est pas installé. Voici comment l'installer:")
    
    if platform.system() == "Darwin":  # macOS
        print("   Sur macOS: brew install direnv")
    elif platform.system() == "Linux":
        print("   Sur Linux: sudo apt install direnv (ou équivalent pour votre distribution)")
    else:  # Windows
        print("   Sur Windows: https://direnv.net/docs/installation.html")
    
    print("\nAprès l'installation, ajoutez ceci à votre ~/.zshrc ou ~/.bashrc:")
    print('eval "$(direnv hook zsh)"  # ou bash selon votre shell')
    
    return False


def setup_direnv():
    """Configure direnv pour le projet"""
    envrc_path = ".envrc"
    
    # Vérifier si le fichier .envrc existe déjà
    if not os.path.exists(envrc_path):
        print("📝 Création du fichier .envrc pour direnv...")
        # Si le fichier n'existe pas déjà, on le crée
        with open(envrc_path, "w") as f:
            f.write("""# Ce fichier est automatiquement utilisé par direnv pour activer l'environnement
# lorsque vous entrez dans le répertoire du projet

# Activer l'environnement virtuel Python
if [ -d .venv ]; then
  export VIRTUAL_ENV=$(pwd)/.venv
  export PATH="$VIRTUAL_ENV/bin:$PATH"
  # Désactiver le prompt par défaut de Python car direnv l'affiche déjà
  export VIRTUAL_ENV_DISABLE_PROMPT=1
fi

# Variables d'environnement du projet
export PYTHONPATH=$(pwd):$PYTHONPATH
export REDIS_HOST=localhost
export REDIS_PORT=6379

# Message d'information
echo "🚀 Environnement Syntinel activé !"
echo "📌 Python: $(python --version 2>&1)"
echo "📁 Path: $PYTHONPATH"
""")
        print("✅ Fichier .envrc créé")
    else:
        print("✅ Fichier .envrc existant détecté")

    # Autoriser le fichier .envrc si direnv est installé
    if shutil.which("direnv"):
        run_command("direnv allow", "Autorisation du fichier .envrc", exit_on_error=False)


def setup_environment():
    """Configure l'environnement de développement"""
    # Vérifier si l'environnement virtuel existe déjà
    if os.path.exists(".venv"):
        print("✅ Environnement virtuel .venv existant détecté")
    else:
        # Création d'un environnement virtuel avec uv
        run_command("uv venv", "Création de l'environnement virtuel")
    
    # Installation des dépendances avec uv (sans besoin d'activer l'environnement)
    run_command("uv pip install -e '.[telegram,writer,dev]'",
              "Installation des dépendances du projet")
    
    # Installation de Playwright pour crawl4ai
    if shutil.which("crawl4ai-setup"):
        print("\n[*] Installation de Playwright pour crawl4ai...")
        run_command("crawl4ai-setup", "Configuration de crawl4ai avec Playwright", exit_on_error=False)
    else:
        print("⚠️ Commande crawl4ai-setup non trouvée. Veuillez l'exécuter manuellement après l'installation:\n   crawl4ai-setup")
    
    # Créer un fichier .last_setup avec le hash de pyproject.toml
    try:
        import hashlib
        with open("pyproject.toml", "rb") as f:
            pyproject_hash = hashlib.md5(f.read()).hexdigest()
        
        os.makedirs(".venv", exist_ok=True)  # Assurer que le dossier .venv existe
        with open(".venv/.last_setup", "w") as f:
            f.write(pyproject_hash)
        print("✅ Marqueur d'environnement à jour créé")
    except Exception as e:
        print(f"⚠️ Impossible de créer le marqueur d'environnement: {e}")
              
    # Configuration de direnv
    setup_direnv()


def main():
    """Fonction principale"""
    print("=" * 50)
    print("🚀 Configuration de l'environnement de développement Syntinel")
    print("=" * 50)
    
    # Vérifie que nous sommes à la racine du projet
    if not os.path.exists("pyproject.toml"):
        print("❌ Erreur: Ce script doit être exécuté depuis la racine du projet Syntinel")
        sys.exit(1)
    
    # Vérifier/installer les outils
    check_uv_installed()
    check_direnv_installed()
    
    # Configurer l'environnement
    setup_environment()
    
    print("\n" + "=" * 50)
    print("✨ Environnement de développement prêt!")
    print("📌 Avec direnv, votre environnement sera activé automatiquement")
    print("   quand vous entrez dans le répertoire du projet")
    print("\n📌 Commandes uv utiles (pas besoin d'activer l'environnement):")
    print("   - uv pip install <package>                  # Installer un package")
    print("   - uv run python scripts/monitor_redis.py    # Exécuter un script")
    print("   - uv pip freeze                            # Lister les dépendances")
    print("=" * 50)


if __name__ == "__main__":
    main()
