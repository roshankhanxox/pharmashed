"""Photos: image processing, the AI check, upload/attach/serve through the routes (fake bucket, fake model)."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from pharmashed_api.assistant import loop
from pharmashed_api.community import auth, photos, storage
from pharmashed_api.community.auth import TokenVerifier
from pharmashed_api.main import app

from .test_community_auth import BASE, KEY, make_token
from .test_community_reports import body


def image_bytes(fmt="PNG", size=(40, 30), exif=False) -> bytes:
    img = Image.new("RGB", size, (30, 90, 160))
    out = io.BytesIO()
    kwargs = {}
    if exif:
        e = Image.Exif()
        e[0x010F] = "SecretCameraMaker"
        e[0x8825] = {1: "N", 2: (43.0, 36.0, 0.0)}   # a GPS block
        kwargs["exif"] = e
    img.save(out, fmt, **kwargs)
    return out.getvalue()


def test_process_shrinks_and_strips_metadata():
    jpeg, w, h = photos.process_image(image_bytes("JPEG", (3000, 2000), exif=True))
    assert max(w, h) == photos.MAX_EDGE and (w, h) == (1280, 853)
    with Image.open(io.BytesIO(jpeg)) as img:
        assert img.format == "JPEG" and len(img.getexif()) == 0
    assert b"SecretCameraMaker" not in jpeg


def test_process_accepts_other_formats_and_modes():
    for fmt in ("PNG", "WEBP", "GIF"):
        assert photos.process_image(image_bytes(fmt))[1:] == (40, 30)
    rgba = io.BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(rgba, "PNG")
    assert photos.process_image(rgba.getvalue())[1] == 10


@pytest.mark.parametrize("raw", [b"", b"not an image", b"%PDF-1.4 hello", b"\x89PNG\r\n\x1a\n" + b"x" * 50])
def test_process_rejects_non_images(raw):
    with pytest.raises(photos.InvalidPhoto):
        photos.process_image(raw)


def test_process_rejects_huge_uploads_and_pixel_bombs():
    with pytest.raises(photos.InvalidPhoto):
        photos.process_image(b"x" * (photos.MAX_UPLOAD_BYTES + 1))
    bomb = io.BytesIO()
    Image.new("1", (9000, 9000)).save(bomb, "PNG")          # 81 MP, tiny file
    with pytest.raises(photos.InvalidPhoto):
        photos.process_image(bomb.getvalue())


class FakeModel:
    def __init__(self, reply):
        self.reply, self.calls = reply, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))])


@pytest.fixture
def model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.delenv("ASSISTANT_PROVIDER", raising=False)

    def install(reply):
        m = FakeModel(reply)
        monkeypatch.setattr(loop, "_client", lambda prov: m)
        return m

    return install


def test_ai_check_outcomes(model):
    m = model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    assert photos.ai_check(b"jpeg") == {"ok": True, "flags": {}}
    sent = m.calls[0]["messages"][0]["content"]
    assert sent[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    model(json.dumps({"is_stream": False, "people": True, "plate": False}))
    assert photos.ai_check(b"jpeg") == {"ok": False, "flags": {"not_a_stream": True, "people": True}}


@pytest.mark.parametrize("reply", ["garbage", "{}", RuntimeError("down")])
def test_ai_check_that_cannot_run_is_unchecked_not_ok(model, reply):
    model(reply)
    assert photos.ai_check(b"jpeg") == {"ok": None, "flags": {"unchecked": True}}


def test_ai_check_needs_a_model_that_reads_images(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "g")
    assert photos.ai_check(b"jpeg")["ok"] is None


class FakeBucket:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def install(self, monkeypatch):
        monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "https://s3.test")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "k")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s")
        monkeypatch.setenv("S3_BUCKET", "uploads")
        monkeypatch.setattr(storage, "put", lambda key, data, ct: self.objects.__setitem__(key, data))
        monkeypatch.setattr(storage, "presigned_get", lambda key, seconds=300: f"https://s3.test/uploads/{key}?sig=1")
        return self


@pytest.fixture
def client(community_db, monkeypatch):
    monkeypatch.setenv("NEON_AUTH_BASE_URL", BASE)
    auth.set_verifier(TokenVerifier(BASE, key_resolver=lambda token: KEY.public_key()))
    yield TestClient(app)
    auth.set_verifier(None)


def bearer(sub="ph-1"):
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def upload(client, sub="ph-1", data=None, name="p.png"):
    return client.post("/api/photos", files={"file": (name, data or image_bytes(), "image/png")}, headers=bearer(sub))


def start(client, sub="ph-1", nick="Photo-Pat"):
    client.put("/api/me/profile", json={"nickname": nick}, headers=bearer(sub))


def test_upload_needs_sign_in_and_storage(client, monkeypatch, model):
    assert client.post("/api/photos", files={"file": ("p.png", image_bytes(), "image/png")}).status_code == 401
    monkeypatch.delenv("S3_BUCKET", raising=False)
    assert upload(client).status_code == 503
    assert client.get("/api/community/status").json()["photos"] is False


def test_good_photo_round_trip(client, monkeypatch, model):
    bucket = FakeBucket().install(monkeypatch)
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    start(client)
    up = upload(client)
    assert up.status_code == 201 and up.json()["ai_ok"] is True
    pid = up.json()["id"]
    assert list(bucket.objects) == [f"photos/{pid}.jpg"]
    made = client.post("/api/reports", json=body(photo_id=pid), headers=bearer()).json()
    assert made["photo_url"] == f"/photos/{pid}"
    r = client.get(f"/api/photos/{pid}", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("https://s3.test/uploads/photos/")
    assert client.get("/api/community/status").json()["photos"] is True


def test_flagged_or_unchecked_photo_holds_the_report_and_stays_private(client, monkeypatch, model):
    FakeBucket().install(monkeypatch)
    start(client)
    model(json.dumps({"is_stream": True, "people": True, "plate": False}))
    pid = upload(client).json()["id"]
    held = client.post("/api/reports", json=body(photo_id=pid), headers=bearer()).json()
    assert held["photo_url"] is None
    assert client.get("/api/me/reports", headers=bearer()).json()[0]["id"] == held["id"]
    assert held["id"] not in [r["id"] for r in client.get("/api/reports?limit=500").json()]
    assert client.get(f"/api/photos/{pid}", follow_redirects=False).status_code == 404   # private until approved
    model("garbage")                                                                      # check could not run
    pid2 = upload(client).json()
    assert pid2["ai_ok"] is None
    client.post("/api/reports", json=body(photo_id=pid2["id"]), headers=bearer())
    assert [r["status"] for r in client.get("/api/me/reports", headers=bearer()).json()] == ["pending", "pending"]


def test_cannot_attach_someone_elses_or_a_used_photo(client, monkeypatch, model):
    FakeBucket().install(monkeypatch)
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    start(client, "ph-1", "Photo-Pat")
    start(client, "ph-2", "Photo-Lee")
    pid = upload(client, "ph-1").json()["id"]
    assert client.post("/api/reports", json=body(photo_id=pid), headers=bearer("ph-2")).status_code == 422
    assert client.post("/api/reports", json=body(photo_id=pid), headers=bearer("ph-1")).status_code == 201
    assert client.post("/api/reports", json=body(photo_id=pid), headers=bearer("ph-1")).status_code == 422
    assert client.post("/api/reports", json=body(photo_id="00000000-0000-0000-0000-000000000000"), headers=bearer("ph-1")).status_code == 422
    # a failed attach must not leave a half-made report behind
    assert len(client.get("/api/me/reports", headers=bearer("ph-2")).json()) == 0


def test_bad_files_and_daily_cap(client, monkeypatch, model):
    FakeBucket().install(monkeypatch)
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    start(client)
    assert upload(client, data=b"not an image").status_code == 422
    codes = [upload(client).status_code for _ in range(photos.MAX_UPLOADS_PER_DAY + 1)]
    assert codes == [201] * photos.MAX_UPLOADS_PER_DAY + [429]


def test_storage_failure_is_a_clean_error(client, monkeypatch, model):
    FakeBucket().install(monkeypatch)
    model(json.dumps({"is_stream": True, "people": False, "plate": False}))
    monkeypatch.setattr(storage, "put", lambda *a: (_ for _ in ()).throw(RuntimeError("bucket down")))
    start(client)
    assert upload(client).status_code == 502


def test_unknown_photo_id_is_404(client):
    assert client.get("/api/photos/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/api/photos/not-a-uuid").status_code == 422
