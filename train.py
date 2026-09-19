import argparse, subprocess, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    if "af" in args.config:
        subprocess.check_call([sys.executable, "-m", "src.af.train", "--config", args.config])
    else:
        subprocess.check_call([sys.executable, "-m", "src.bs.train", "--config", args.config])

if __name__ == "__main__":
    main()