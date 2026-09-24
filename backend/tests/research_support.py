import hashlib
import struct
import zlib
from uuid import uuid4


def png(width=2, height=2):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = b"".join(b"\x00" + b"\x22\x88\xaa" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def policy(client, base, headers):
    response = client.post(
        base + "/retention-policies",
        headers=headers,
        json={
            "policy_key": uuid4().hex,
            "version": 1,
            "raw_days": 30,
            "media_days": 7,
            "derived_days": 30,
            "export_days": 1,
            "legal_basis": "synthetic-development-policy",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def document(client, base, headers, purpose="study", locale="fr", key=None):
    response = client.post(
        base + "/consent-documents",
        headers=headers,
        json={
            "document_key": key or uuid4().hex,
            "version": 1,
            "locale": locale,
            "purpose": purpose,
            "body": "Texte de consentement تجريبي",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(
    client,
    base,
    headers,
    content=None,
    media_type="image/png",
    extension="png",
    purpose="stimulus",
    complete=True,
    policy_id=None,
):
    content = content if content is not None else png()
    response = client.post(
        base + "/upload-intents",
        headers=headers,
        json={
            "upload_key": uuid4().hex,
            "filename": "fixture." + extension,
            "media_type": media_type,
            "purpose": purpose,
            "size_bytes": len(content),
            "checksum": hashlib.sha256(content).hexdigest(),
            "retention_policy_id": policy_id or policy(client, base, headers),
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    endpoint = base + "/upload-intents/" + result["upload_id"]
    response = client.put(
        endpoint + "/content", headers=headers | {"content-type": media_type}, content=content
    )
    assert response.status_code == 204, response.text
    if complete:
        response = client.post(endpoint + "/complete", headers=headers)
        assert response.status_code == 200, response.text
        result["asset"] = response.json()
    return result
