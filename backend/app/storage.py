from pathlib import Path

from app.config import settings
from botocore.exceptions import BotoCoreError, ClientError


def _client():
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("S3 storage requires boto3") from exc
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def _storage_error() -> RuntimeError:
    return RuntimeError("Object storage operation failed")


def put_file(path: Path, object_key: str) -> str:
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        try:
            _client().upload_file(str(path), settings.s3_bucket, object_key)
        except (BotoCoreError, ClientError) as exc:
            raise _storage_error() from exc
        return f"s3://{settings.s3_bucket}/{object_key}"
    return str(path)


def delete_file(path: Path, object_key: str | None = None) -> None:
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        try:
            _client().delete_object(
                Bucket=settings.s3_bucket,
                Key=object_key or path.name,
            )
        except (BotoCoreError, ClientError) as exc:
            raise _storage_error() from exc
        return
    path.unlink(missing_ok=True)
