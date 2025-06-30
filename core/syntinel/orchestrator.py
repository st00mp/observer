from core.syntinel.modules.ingestion.ingestion_pipeline import run_ingestion
from core.syntinel.modules.scoring.service import score_all_unprocessed
from core.syntinel.modules.publishing.service import maybe_auto_publish


def full_run():
    print("=== [1] Ingestion started ===")
    run_ingestion()

    print("=== [2] Scoring started ===")
    score_all_unprocessed()

    print("=== [3] Publishing step ===")
    maybe_auto_publish()


if __name__ == "__main__":
    full_run()
