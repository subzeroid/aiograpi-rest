import json
import os
import tempfile

from aiograpi.exceptions import PhotoConfigureStoryError, VideoConfigureStoryError
from aiograpi.story import StoryBuilder
from aiograpi.types import Location, Usertag
from fastapi import HTTPException
from pydantic import ValidationError

STORY_CONFIGURE_WITHOUT_MEDIA = "configure succeeded without media payload"
USERTAGS_FORM_DESCRIPTION = (
    "Repeat this form field with a JSON-encoded Usertag object, "
    "or pass one JSON array of Usertag objects. Leave empty to omit."
)
LOCATION_FORM_DESCRIPTION = "JSON-encoded Location object. Leave empty to omit."


def _is_blank_form_value(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _invalid_json_form_field(field_name: str, exc: Exception):
    raise HTTPException(
        status_code=422,
        detail=f"Invalid JSON object for form field '{field_name}'",
    ) from exc


def parse_json_form_models(values, model, field_name: str):
    parsed = []
    for raw_value in values or []:
        if _is_blank_form_value(raw_value):
            continue
        try:
            payload = json.loads(raw_value)
            items = payload if isinstance(payload, list) else [payload]
            parsed.extend(model.model_validate(item) for item in items)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
            _invalid_json_form_field(field_name, exc)
    return parsed


def parse_json_form_model(value, model, field_name: str):
    if _is_blank_form_value(value):
        return None
    try:
        return model.model_validate(json.loads(value))
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
        _invalid_json_form_field(field_name, exc)


def parse_upload_usertags(usertags):
    return parse_json_form_models(usertags, Usertag, "usertags")


def parse_upload_location(location):
    return parse_json_form_model(location, Location, "location")


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
