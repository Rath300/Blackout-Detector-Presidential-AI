from core.services import ml_risk


def main():
    model = ml_risk.train_and_cache_model()
    if model:
        print("Model trained and county risk cached.")
    else:
        print("No storm event data found.")


if __name__ == "__main__":
    main()
