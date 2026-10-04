from __future__ import annotations

import hashlib
import mimetypes
import os
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlparse

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.core.config import settings


ALLOWED_MEDIA_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "video/mp4": {".mp4", ".m4v"},
    "video/webm": {".webm"},
    "video/quicktime": {".mov"},
}


@dataclass(frozen=True)
class StoredMedia:
    reference: str
    backend: str
    bucket: str
    object_key: str
    original_name: str
    content_type: str
    size_bytes: int
    sha256: str


def _local_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_original_name(name: str | None) -> str:
    return Path(name or "upload.bin").name[:255]


def _content_type(file: UploadFile, suffix: str) -> str:
    supplied = (file.content_type or "").lower().split(";", 1)[0].strip()
    guessed = (mimetypes.guess_type(f"x{suffix}")[0] or "").lower()
    media_type = supplied if supplied in ALLOWED_MEDIA_TYPES else guessed
    if media_type not in ALLOWED_MEDIA_TYPES or suffix not in ALLOWED_MEDIA_TYPES[media_type]:
        raise HTTPException(400, "只支持 JPG、PNG、WebP、MP4、WebM 或 MOV 媒体文件")
    return media_type


def _validate_signature(header: bytes, content_type: str) -> None:
    valid = {
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP",
        "video/mp4": len(header) >= 12 and header[4:8] == b"ftyp",
        "video/quicktime": len(header) >= 12 and header[4:8] == b"ftyp",
        "video/webm": header.startswith(b"\x1a\x45\xdf\xa3"),
    }.get(content_type, False)
    if not valid:
        raise HTTPException(400, "文件内容与声明的媒体格式不一致")


def _s3_client():
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - deployment configuration error
        raise RuntimeError("S3 存储需要安装 boto3") from exc
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        aws_access_key_id=settings.s3_access_key_id or None,
        aws_secret_access_key=settings.s3_secret_access_key or None,
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.s3_force_path_style else "virtual"},
        ),
    )


def save_upload(file: UploadFile, *, prefix: str) -> StoredMedia:
    original = _safe_original_name(file.filename)
    suffix = Path(original).suffix.lower()
    content_type = _content_type(file, suffix)
    limit = settings.max_upload_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    with tempfile.SpooledTemporaryFile(max_size=min(limit, 8 * 1024 * 1024)) as spool:
        header = b""
        while chunk := file.file.read(1024 * 1024):
            if not header:
                header = chunk[:32]
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f"单个文件不能超过 {settings.max_upload_mb} MB")
            digest.update(chunk)
            spool.write(chunk)
        if size == 0:
            raise HTTPException(400, "不能上传空文件")
        _validate_signature(header, content_type)
        spool.seek(0)

        now = datetime.now(timezone.utc)
        safe_prefix = str(PurePosixPath(prefix.strip("/")))
        object_key = f"{safe_prefix}/{now:%Y/%m}/{uuid.uuid4().hex}{suffix}"
        backend = settings.media_storage_backend.lower()
        bucket = settings.s3_bucket if backend == "s3" else ""
        if backend == "s3":
            if not bucket:
                raise RuntimeError("S3_BUCKET 未配置")
            _s3_client().upload_fileobj(
                spool,
                bucket,
                object_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": {"sha256": digest.hexdigest(), "original-name": quote(original)},
                },
            )
        elif backend == "local":
            root = _local_root()
            destination = (root / Path(object_key)).resolve()
            if root not in destination.parents:
                raise RuntimeError("非法媒体对象键")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("wb") as output:
                    while chunk := spool.read(1024 * 1024):
                        output.write(chunk)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            raise RuntimeError(f"不支持的 MEDIA_STORAGE_BACKEND: {backend}")

    reference_bucket = bucket or "_"
    reference = f"media://{backend}/{quote(reference_bucket, safe='')}/{quote(object_key, safe='/')}"
    return StoredMedia(reference, backend, bucket, object_key, original, content_type, size, digest.hexdigest())


def parse_reference(reference: str) -> tuple[str, str, str]:
    parsed = urlparse(reference)
    if parsed.scheme != "media" or parsed.netloc not in {"local", "s3"}:
        raise ValueError("不是有效的媒体引用")
    parts = parsed.path.lstrip("/").split("/", 1)
    if len(parts) != 2:
        raise ValueError("媒体引用缺少对象键")
    bucket = unquote(parts[0])
    return parsed.netloc, "" if parsed.netloc == "local" and bucket == "_" else bucket, unquote(parts[1])


def download_response(reference: str, *, download_name: str | None = None) -> Response:
    backend, bucket, object_key = parse_reference(reference)
    if backend == "local":
        root = _local_root()
        path = (root / Path(object_key)).resolve()
        if root not in path.parents or not path.is_file():
            raise HTTPException(404, "文件不存在")
        return FileResponse(path, filename=download_name)
    url = _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=settings.s3_presign_expire_seconds,
    )
    return RedirectResponse(url=url, status_code=307)


@contextmanager
def materialize(reference: str):
    """为 OCR 等只接受本地路径的库提供短生命周期文件。"""
    backend, bucket, object_key = parse_reference(reference)
    if backend == "local":
        path = (_local_root() / Path(object_key)).resolve()
        if not path.is_file():
            raise FileNotFoundError(object_key)
        yield path
        return
    suffix = Path(object_key).suffix
    fd, name = tempfile.mkstemp(prefix="hebgwd-media-", suffix=suffix)
    os.close(fd)
    path = Path(name)
    try:
        _s3_client().download_file(bucket, object_key, str(path))
        yield path
    finally:
        path.unlink(missing_ok=True)


def delete_media(stored: StoredMedia) -> None:
    if stored.backend == "local":
        root = _local_root()
        path = (root / Path(stored.object_key)).resolve()
        if root in path.parents:
            path.unlink(missing_ok=True)
    elif stored.backend == "s3":
        _s3_client().delete_object(Bucket=stored.bucket, Key=stored.object_key)


def assert_storage_ready() -> None:
    """生产就绪探针使用：确认应用凭据可以访问目标私有桶。"""
    if settings.media_storage_backend.lower() == "s3":
        _s3_client().head_bucket(Bucket=settings.s3_bucket)
    else:
        root = _local_root()
        if not os.access(root, os.W_OK):
            raise RuntimeError(f"媒体目录不可写: {root}")
