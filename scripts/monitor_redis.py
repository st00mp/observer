#!/usr/bin/env python3
"""
Redis Stream Monitor for Syntinel

Ce script permet de visualiser en temps réel les données qui transitent
par Redis dans le système Syntinel. Il offre une vue pédagogique du
fonctionnement des streams Redis et de leur utilisation dans l'architecture.

Usage:
    python monitor_redis.py [--host HOSTNAME] [--port PORT] [--streams STREAM1 STREAM2 ...]
    
Example:
    python monitor_redis.py --streams new_articles 
"""

import os
import sys
import time
import json
import argparse
import datetime
import redis
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

# Configuration par défaut
DEFAULT_HOST = os.getenv("REDIS_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("REDIS_PORT", 6379))
DEFAULT_STREAMS = ["new_articles"]  # Stream par défaut à surveiller

# Configuration de l'affichage
console = Console()


class StreamMonitor:
    """Moniteur de streams Redis pour Syntinel."""
    
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT, streams=None, max_events=50):
        """Initialise le moniteur de streams Redis.
        
        Args:
            host (str): Hôte Redis
            port (int): Port Redis
            streams (list): Liste des noms de streams à surveiller
            max_events (int): Nombre maximum d'événements à conserver en mémoire
        """
        self.host = host
        self.port = port
        self.streams = streams or DEFAULT_STREAMS
        self.redis = None
        self.events = []
        self.stream_ids = {stream: "0-0" for stream in self.streams}
        self.max_events = max_events
        self.start_time = datetime.datetime.now()
        
    def connect(self):
        """Établit la connexion avec Redis."""
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=True
            )
            console.print(f"[green]Connecté à Redis {self.host}:{self.port}[/green]")
            return True
        except redis.exceptions.ConnectionError as e:
            console.print(f"[red]Erreur de connexion: {e}[/red]")
            return False
    
    def get_stream_info(self, stream_name):
        """Récupère des informations sur le stream.
        
        Args:
            stream_name (str): Nom du stream Redis
            
        Returns:
            dict: Informations sur le stream (length, etc.)
        """
        try:
            info = self.redis.xinfo_stream(stream_name)
            return info
        except redis.exceptions.ResponseError:
            # Le stream n'existe peut-être pas encore
            return {"length": 0, "groups": 0, "last-entry": None}
    
    def fetch_events(self):
        """Récupère les nouveaux événements depuis les streams surveillés."""
        if not self.redis:
            return
            
        for stream in self.streams:
            # Récupérer les nouveaux messages depuis la dernière ID lue
            try:
                response = self.redis.xread({stream: self.stream_ids[stream]}, count=100, block=100)
                
                if response:
                    for stream_name, messages in response:
                        for message_id, data in messages:
                            # Mettre à jour l'ID de lecture pour ce stream
                            self.stream_ids[stream_name] = message_id
                            
                            # Enregistrer l'événement
                            event = {
                                "timestamp": datetime.datetime.now(),
                                "stream": stream_name,
                                "id": message_id,
                                "data": data
                            }
                            self.events.append(event)
                            
                            # Limiter la taille de l'historique
                            if len(self.events) > self.max_events:
                                self.events.pop(0)
            except redis.exceptions.ConnectionError as e:
                console.print(f"[red]Connexion perdue: {e}[/red]")
                # Tentative de reconnexion
                time.sleep(1)
                self.connect()
    
    def generate_layout(self):
        """Génère la mise en page de l'interface.
        
        Returns:
            Layout: Layout Rich pour l'affichage
        """
        # Création du layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # En-tête avec informations générales
        header = Text("SYNTINEL REDIS MONITOR", justify="center", style="bold white on blue")
        runtime = (datetime.datetime.now() - self.start_time).total_seconds()
        header.append(f"\nConnexion: {self.host}:{self.port} | Streams: {', '.join(self.streams)} | Temps d'exécution: {int(runtime)}s", style="cyan")
        layout["header"].update(Panel(header))
        
        # Corps avec table d'événements
        table = Table(box=ROUNDED, expand=True)
        table.add_column("Heure", style="cyan", width=10)
        table.add_column("Stream", style="green")
        table.add_column("Message ID", style="yellow")
        table.add_column("Données", style="white")
        
        # Ajouter les événements à la table (du plus récent au plus ancien)
        for event in reversed(self.events):
            timestamp = event["timestamp"].strftime("%H:%M:%S")
            stream = event["stream"]
            msg_id = event["id"]
            try:
                # Formater les données JSON proprement
                data_str = json.dumps(event["data"], indent=2, ensure_ascii=False)
            except:
                data_str = str(event["data"])
                
            table.add_row(timestamp, stream, msg_id, data_str)
            
        layout["body"].update(table)
        
        # Pied de page avec statistiques
        stats = []
        for stream in self.streams:
            info = self.get_stream_info(stream)
            stats.append(f"{stream}: {info.get('length', 0)} messages")
        
        footer_text = Text(f"Statistiques des streams: {' | '.join(stats)}", justify="center")
        footer_text.append("\nCtrl+C pour quitter", style="dim")
        layout["footer"].update(Panel(footer_text))
        
        return layout
    
    def run(self):
        """Exécute le moniteur en continu."""
        if not self.connect():
            return
            
        try:
            with Live(self.generate_layout(), refresh_per_second=4, screen=True) as live:
                while True:
                    self.fetch_events()
                    live.update(self.generate_layout())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            console.print("[yellow]Arrêt du moniteur...[/yellow]")
        finally:
            if self.redis:
                self.redis = None


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description="Moniteur de streams Redis pour Syntinel")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Hôte Redis (défaut: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port Redis (défaut: {DEFAULT_PORT})")
    parser.add_argument("--streams", nargs="+", default=DEFAULT_STREAMS, 
                        help=f"Streams à surveiller (défaut: {' '.join(DEFAULT_STREAMS)})")
    parser.add_argument("--max-events", type=int, default=50, 
                        help="Nombre maximum d'événements à afficher (défaut: 50)")
    
    args = parser.parse_args()
    
    try:
        monitor = StreamMonitor(
            host=args.host,
            port=args.port,
            streams=args.streams,
            max_events=args.max_events
        )
        monitor.run()
    except Exception as e:
        console.print(f"[bold red]Erreur: {e}[/bold red]")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
