import os
import tempfile

from aiograpi.exceptions import PhotoConfigureStoryError, VideoConfigureStoryError
from aiograpi.story import StoryBuilder

STORY_CONFIGURE_WITHOUT_MEDIA = "configure succeeded without media payload"


def _write_temp_file(directory, content, suffix):
    fp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, dir=directory)
    try:
        fp.write(content)
        return fp.name
    finally:
        fp.close()


def _normalize_thumbnail(kwargs, directory):
    kwargs = dict(kwargs)
    thumbnail = kwargs.get('thumbnail')
    if isinstance(thumbnail, (bytes, bytearray)):
        kwargs['thumbnail'] = _write_temp_file(directory, thumbnail, '.jpg')
    return kwargs


async def _latest_story_after_configure_without_media(cl, exc):
    if STORY_CONFIGURE_WITHOUT_MEDIA not in str(exc):
        raise exc
    user_id = getattr(cl, "user_id", None)
    if not user_id:
        raise exc
    try:
        stories = await cl.user_stories(user_id, amount=5)
    except Exception:
        raise exc
    if not stories:
        raise exc
    return stories[0]


async def photo_upload_story_as_video(cl, content, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.jpg') as fp:
        fp.write(content)
        mentions = kwargs.get('mentions') or []
        caption = kwargs.get('caption') or ''
        video = StoryBuilder(fp.name, caption, mentions).photo(15)
        try:
            return await cl.video_upload_to_story(video.path, **kwargs)
        except (PhotoConfigureStoryError, VideoConfigureStoryError) as exc:
            return await _latest_story_after_configure_without_media(cl, exc)


async def photo_upload_story_as_photo(cl, content, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.jpg') as fp:
        fp.write(content)
        try:
            return await cl.photo_upload_to_story(fp.name, **kwargs)
        except (PhotoConfigureStoryError, VideoConfigureStoryError) as exc:
            return await _latest_story_after_configure_without_media(cl, exc)


async def video_upload_story(cl, content, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.mp4') as fp:
        fp.write(content)
        mentions = kwargs.get('mentions') or []
        caption = kwargs.get('caption') or ''
        video = StoryBuilder(fp.name, caption, mentions).video(15)
        try:
            return await cl.video_upload_to_story(video.path, **kwargs)
        except (PhotoConfigureStoryError, VideoConfigureStoryError) as exc:
            return await _latest_story_after_configure_without_media(cl, exc)


async def photo_upload_post(cl, content, **kwargs):
    with tempfile.NamedTemporaryFile(suffix='.jpg') as fp:
        fp.write(content)
        return await cl.photo_upload(fp.name, **kwargs)


async def video_upload_post(cl, content, **kwargs):
    with tempfile.TemporaryDirectory() as td:
        path = _write_temp_file(td, content, '.mp4')
        return await cl.video_upload(path, **_normalize_thumbnail(kwargs, td))


async def album_upload_post(cl, files, **kwargs):
    with tempfile.TemporaryDirectory() as td:
        paths = []
        for i in range(len(files)):
            filename, ext = os.path.splitext(files[i].filename)
            fp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, dir=td)
            fp.write(await files[i].read())
            fp.close()
            paths.append(fp.name)
        return await cl.album_upload(paths, **kwargs)


async def igtv_upload_post(cl, content, **kwargs):
    with tempfile.TemporaryDirectory() as td:
        path = _write_temp_file(td, content, '.mp4')
        return await cl.igtv_upload(path, **_normalize_thumbnail(kwargs, td))


async def clip_upload_post(cl, content, **kwargs):
    with tempfile.TemporaryDirectory() as td:
        path = _write_temp_file(td, content, '.mp4')
        return await cl.clip_upload(path, **_normalize_thumbnail(kwargs, td))
