import os, argparse
import pandas as pd
from src.common.seed import set_seed
from src.af.infer import infer_af
from src.bs.infer import infer_bs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="каталог с тестовыми чипами и sample_submission.csv")
    ap.add_argument("--output", required=True, help="путь к submission.csv")
    ap.add_argument("--train-dir", default="train", help="каталог train (для вспомогательных слоёв)")
    ap.add_argument("--af-weights", default="weights/af")
    ap.add_argument("--bs-weights", default="weights/bs")
    args = ap.parse_args()

    set_seed(42)

    # 1) Читаем шаблон — порядок строк сохраняем
    sample = pd.read_csv(os.path.join(args.data_dir, "sample_submission.csv"))

    # 2) AF
    af_df = infer_af(args.train_dir, args.data_dir, "/tmp/af.csv", args.af_weights)
    # 3) BS
    bs_rows = infer_bs(args.train_dir, args.data_dir, args.bs_weights)
    bs_df = pd.DataFrame(bs_rows)

    # 4) Собираем в порядке шаблона
    full = pd.concat([af_df, bs_df], ignore_index=True)
    full = full.set_index(["chip_id", "class_id"])
    sample = sample.set_index(["chip_id", "class_id"])
    sample["rle"] = full["rle"]
    sample = sample.reset_index()
    sample["rle"] = sample["rle"].fillna("")

    # 5) Записываем
    sample.to_csv(args.output, index=False)
    print(f"Saved {args.output} with {len(sample)} rows")

if __name__ == "__main__":
    main()