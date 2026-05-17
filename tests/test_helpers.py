from pathlib import Path
from types import SimpleNamespace

import pytest
from aiograpi.exceptions import PhotoConfigureStoryError, VideoConfigureStoryError

import helpers


class FakeUploadFile:
    def __init__(self, filename, content):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


class FakeClient:
    def __init__(self):
        self.calls = []

    async def photo_upload(self, path, **kwargs):
        self.calls.append(("photo_upload", path, kwargs))
        return Path(path)

    async def video_upload(self, path, **kwargs):
        self.calls.append(("video_upload", path, kwargs))
        return Path(path)

    async def album_upload(self, paths, **kwargs):
        self.calls.append(("album_upload", tuple(paths), kwargs))
        return list(paths)

    async def igtv_upload(self, path, **kwargs):
        self.calls.append(("igtv_upload", path, kwargs))
        return Path(path)

    async def clip_upload(self, path, **kwargs):
        self.calls.append(("clip_upload", path, kwargs))
        return Path(path)

    async def photo_upload_to_story(self, path, **kwargs):
        self.calls.append(("photo_upload_to_story", path, kwargs))
        return Path(path)

    async def video_upload_to_story(self, path, **kwargs):
        self.calls.append(("video_upload_to_story", path, kwargs))
        return Path(path)


class FakeConfigureWithoutMediaClient(FakeClient):
    user_id = "42"

    async def photo_upload_to_story(self, path, **kwargs):
        self.calls.append(("photo_upload_to_story", path, kwargs))
        raise PhotoConfigureStoryError("Photo story upload configure succeeded without media payload")

    async def user_stories(self, user_id, amount=0):
        self.calls.append(("user_stories", user_id, amount))
        return [SimpleNamespace(pk="new-story", id="new-story_42", media_type=1)]


class FakeVideoConfigureWithoutMediaClient(FakeConfigureWithoutMediaClient):
    async def video_upload_to_story(self, path, **kwargs):
        self.calls.append(("video_upload_to_story", path, kwargs))
        raise VideoConfigureStoryError("Video story upload configure succeeded without media payload")


@pytest.fixture
def fake_storybuilder(monkeypatch):
    class FakeStoryBuilder:
        def __init__(self, path, caption="", mentions=None, bgpath=None):
            self.path = path
            self.caption = caption
            self.mentions = mentions or []

        def photo(self, duration):
            return SimpleNamespace(path=self.path)

        def video(self, duration):
            return SimpleNamespace(path=self.path)

    monkeypatch.setattr(helpers, "StoryBuilder", FakeStoryBuilder)


@pytest.mark.asyncio
async def test_photo_upload_story_as_photo_writes_tempfile_and_calls_client():
    cl = FakeClient()
    result = await helpers.photo_upload_story_as_photo(cl, b"image", caption="cap")
    assert any(call[0] == "photo_upload_to_story" for call in cl.calls)
    path = cl.calls[0][1]
    assert path.endswith(".jpg")
    assert result.suffix == ".jpg"


@pytest.mark.asyncio
async def test_photo_upload_story_as_photo_falls_back_to_created_story_when_configure_has_no_media():
    cl = FakeConfigureWithoutMediaClient()
    result = await helpers.photo_upload_story_as_photo(cl, b"image", caption="cap")
    assert result.pk == "new-story"
    assert ("user_stories", "42", 5) in cl.calls


@pytest.mark.asyncio
async def test_photo_upload_story_as_video_falls_back_to_created_story(fake_storybuilder):
    cl = FakeVideoConfigureWithoutMediaClient()
    result = await helpers.photo_upload_story_as_video(cl, b"image", caption="cap")
    assert result.pk == "new-story"
    assert any(call[0] == "video_upload_to_story" for call in cl.calls)


@pytest.mark.asyncio
async def test_video_upload_story_falls_back_to_created_story(fake_storybuilder):
    cl = FakeVideoConfigureWithoutMediaClient()
    result = await helpers.video_upload_story(cl, b"video", caption="cap")
    assert result.pk == "new-story"
    assert any(call[0] == "video_upload_to_story" for call in cl.calls)


@pytest.mark.asyncio
async def test_configure_without_media_fallback_reraises_unrelated_error():
    exc = PhotoConfigureStoryError("different upload failure")
    with pytest.raises(PhotoConfigureStoryError, match="different upload failure"):
        await helpers._latest_story_after_configure_without_media(SimpleNamespace(user_id="42"), exc)


@pytest.mark.asyncio
async def test_configure_without_media_fallback_requires_user_id():
    exc = PhotoConfigureStoryError("Photo story upload configure succeeded without media payload")
    with pytest.raises(PhotoConfigureStoryError, match="without media payload"):
        await helpers._latest_story_after_configure_without_media(SimpleNamespace(), exc)


@pytest.mark.asyncio
async def test_configure_without_media_fallback_reraises_when_user_stories_fails():
    class Client:
        user_id = "42"

        async def user_stories(self, user_id, amount=0):
            raise RuntimeError("network")

    exc = PhotoConfigureStoryError("Photo story upload configure succeeded without media payload")
    with pytest.raises(PhotoConfigureStoryError, match="without media payload"):
        await helpers._latest_story_after_configure_without_media(Client(), exc)


@pytest.mark.asyncio
async def test_configure_without_media_fallback_reraises_when_no_stories_found():
    class Client:
        user_id = "42"

        async def user_stories(self, user_id, amount=0):
            return []

    exc = PhotoConfigureStoryError("Photo story upload configure succeeded without media payload")
    with pytest.raises(PhotoConfigureStoryError, match="without media payload"):
        await helpers._latest_story_after_configure_without_media(Client(), exc)


@pytest.mark.asyncio
async def test_photo_upload_story_as_video_uses_storybuilder(fake_storybuilder):
    cl = FakeClient()
    result = await helpers.photo_upload_story_as_video(cl, b"image", caption="cap")
    assert any(call[0] == "video_upload_to_story" for call in cl.calls)
    assert str(result).endswith(".jpg")


@pytest.mark.asyncio
async def test_video_upload_story_uses_storybuilder(fake_storybuilder):
    cl = FakeClient()
    result = await helpers.video_upload_story(cl, b"video", caption="cap")
    assert any(call[0] == "video_upload_to_story" for call in cl.calls)
    assert str(result).endswith(".mp4")


@pytest.mark.asyncio
async def test_photo_upload_post_writes_tempfile_and_calls_client():
    cl = FakeClient()
    result = await helpers.photo_upload_post(cl, b"image", caption="hi")
    assert any(call[0] == "photo_upload" for call in cl.calls)
    assert str(result).endswith(".jpg")


@pytest.mark.asyncio
async def test_video_upload_post_writes_tempfile_and_calls_client():
    cl = FakeClient()
    result = await helpers.video_upload_post(cl, b"video", caption="hi")
    assert any(call[0] == "video_upload" for call in cl.calls)
    assert str(result).endswith(".mp4")


@pytest.mark.asyncio
async def test_video_upload_post_writes_thumbnail_bytes_to_tempfile():
    cl = FakeClient()
    await helpers.video_upload_post(cl, b"video", caption="hi", thumbnail=b"thumb")
    call = next(c for c in cl.calls if c[0] == "video_upload")
    thumbnail = call[2]["thumbnail"]
    assert isinstance(thumbnail, str)
    assert thumbnail.endswith(".jpg")


@pytest.mark.asyncio
async def test_igtv_upload_post_writes_tempfile_and_calls_client():
    cl = FakeClient()
    result = await helpers.igtv_upload_post(cl, b"vid", title="t", caption="hi")
    assert any(call[0] == "igtv_upload" for call in cl.calls)
    assert str(result).endswith(".mp4")


@pytest.mark.asyncio
async def test_igtv_upload_post_writes_thumbnail_bytes_to_tempfile():
    cl = FakeClient()
    await helpers.igtv_upload_post(cl, b"vid", title="t", caption="hi", thumbnail=b"thumb")
    call = next(c for c in cl.calls if c[0] == "igtv_upload")
    thumbnail = call[2]["thumbnail"]
    assert isinstance(thumbnail, str)
    assert thumbnail.endswith(".jpg")


@pytest.mark.asyncio
async def test_clip_upload_post_writes_tempfile_and_calls_client():
    cl = FakeClient()
    result = await helpers.clip_upload_post(cl, b"vid", caption="hi")
    assert any(call[0] == "clip_upload" for call in cl.calls)
    assert str(result).endswith(".mp4")


@pytest.mark.asyncio
async def test_clip_upload_post_writes_thumbnail_bytes_to_tempfile():
    cl = FakeClient()
    await helpers.clip_upload_post(cl, b"vid", caption="hi", thumbnail=b"thumb")
    call = next(c for c in cl.calls if c[0] == "clip_upload")
    thumbnail = call[2]["thumbnail"]
    assert isinstance(thumbnail, str)
    assert thumbnail.endswith(".jpg")


@pytest.mark.asyncio
async def test_album_upload_post_collects_files_into_tempdir():
    cl = FakeClient()
    files = [FakeUploadFile("a.jpg", b"img-1"), FakeUploadFile("b.png", b"img-2")]
    result = await helpers.album_upload_post(cl, files, caption="hi")
    call = next(c for c in cl.calls if c[0] == "album_upload")
    paths = call[1]
    assert len(paths) == 2
    assert paths[0].endswith(".jpg")
    assert paths[1].endswith(".png")
    assert len(result) == 2
