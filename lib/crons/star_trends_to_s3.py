import json
import os
import sys
from pathlib import Path

import boto3

path_to_utils = Path(__file__).parent.parent / "stars"
sys.path.insert(0, str(path_to_utils))

from stars import StarEvents

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", None)
BUCKET_NAME = os.environ.get("BUCKET_NAME", "data.ghtrending.io")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
STAR_TRENDS_PATH = os.environ.get("STAR_TRENDS_PATH", "trends/stars")
CACHE_CONTROL = str(os.environ.get("CACHE_CONTROL", "7200"))


def upload_to_s3(result):
    """
    Uploads files to S3
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f"{STAR_TRENDS_PATH}/{result['name']}.json",
        Body=json.dumps(result["data"]),
        ContentType="application/json",
    )


def set_cache_control():
    """
    Sets cache control headers for all objects in the STAR_TRENDS_PATH/* directory
    """
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    for summary in bucket.objects.filter(Prefix=f"{STAR_TRENDS_PATH}/"):
        obj = summary.Object()
        obj.copy_from(
            CopySource={
                "Bucket": BUCKET_NAME,
                "Key": obj.key,
            },
            Metadata=obj.metadata,  # This copies existing metadata
            CacheControl=f"public,max-age={CACHE_CONTROL}",
            ContentType="application/json",
            MetadataDirective="REPLACE",
        )


def main():
    if AWS_ACCESS_KEY_ID is None or AWS_SECRET_ACCESS_KEY is None:
        print("AWS credentials not set. Exiting.")
        sys.exit(1)

    # Get Star Event Trends
    star_events = StarEvents()

    results = []

    # Get the most stared repos from all time from the DB
    print("Getting most stared repos from all time")
    results.append({"name": "all_time", "data": star_events.get_most_stared()})

    # Get the most stared repos from the past 24 hours
    print("Getting most stared repos from the past 24 hours")
    results.append(
        {"name": "last_24_hours", "data": star_events.get_most_stared(hours=24)}
    )

    # Get the most stared repos from the past 7 days
    print("Getting most stared repos from the past 7 days")
    results.append(
        {"name": "last_7_days", "data": star_events.get_most_stared(hours=24 * 7)}
    )

    # Get the most stared repos from the past 30 days
    print("Getting most stared repos from the past 30 days")
    results.append(
        {"name": "last_30_days", "data": star_events.get_most_stared(hours=24 * 30)}
    )

    star_events.close()

    # Upload to S3
    print("Uploading to S3...")
    for result in results:
        upload_to_s3(result)

    print(f"Setting Cache-Control for {STAR_TRENDS_PATH}/* objects...")

    set_cache_control()

    print("Done!")


if __name__ == "__main__":
    main()
