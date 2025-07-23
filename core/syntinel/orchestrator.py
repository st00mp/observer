import argparse
from core.syntinel.modules.ingestion.pipeline import run_ingestion
# from core.syntinel.modules.scoring.service import score_all_unprocessed
# from core.syntinel.modules.publishing.service import maybe_auto_publish


def full_run(export_json=False, export_path=None):
    """
    Exécute le pipeline complet de Syntinel.
    
    Args:
        export_json (bool): Si True, exporte les articles collectés au format JSON
        export_path (str): Chemin du fichier d'export JSON
    """
    print("=== [1] Ingestion started ===")
    run_ingestion(export_json=export_json, export_path=export_path)

    # print("=== [2] Scoring started ===")
    # score_all_unprocessed()

    # print("=== [3] Publishing step ===")
    # maybe_auto_publish()


if __name__ == "__main__":
    # Analyse des arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Syntinel - Pipeline d'ingestion d'articles crypto")
    parser.add_argument(
        "--export-json", 
        action="store_true",
        help="Exporter les articles collectés au format JSON"
    )
    parser.add_argument(
        "--export-path",
        type=str,
        help="Chemin du fichier d'export JSON (si --export-json est activé)"
    )
    args = parser.parse_args()
    
    # Exécution du pipeline avec les options d'export
    full_run(export_json=args.export_json, export_path=args.export_path)
