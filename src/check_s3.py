from pathlib import Path
import os
import subprocess

from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(".env"))

    endpoint_url = os.environ["S3_ENDPOINT_URL"]
    bucket = os.environ["S3_BUCKET"]
    profile = os.environ["AWS_PROFILE"]

    cmd = [
        "aws",
        "s3",
        "ls",
        f"s3://{bucket}/",
        "--endpoint-url",
        endpoint_url,
        "--profile",
        profile,
    ]

    print("Running:")
    print(" ".join(cmd))
    print()

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
