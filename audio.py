import requests
import config
import subprocess
import os
import uuid

GOOGLE_URL = "http://translate.google.com/translate_tts"


class ConversionError(Exception):
    pass


def generate(filename, sentences):
    if not os.path.exists(config.AUDIO_DIR):
        subprocess.check_call(['mkdir', '-p', config.AUDIO_DIR])

    filepath = os.path.join(config.AUDIO_DIR, filename)

    if os.path.exists(filepath):
        return filename

    files = [generate_audio_file(s) for s in sentences]
    merge_files(files, filepath)

    return filename


def generate_audio_file(sentence):
    try:
        return generate_google_tts(sentence)
    except ConversionError:
        return generate_espeak(sentence)


def generate_google_tts(sentence):
    if len(sentence) > 100:
        raise ConversionError("sentence too long")

    filepath = unique_filepath('mp3')

    params = {'ie': 'UTF-8', 'tl': 'fr', 'q': sentence.encode('utf8')}
    response = requests.get(GOOGLE_URL, params=params, stream=True)

    if response.status_code != 200:
        raise ConversionError("google translate responded with {}".format(response.status_code))

    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(1024 * 1024):
            f.write(chunk)

    return filepath


def unique_filepath(extension):
    name = "{}.{}".format(uuid.uuid4(), extension)
    return os.path.join(config.AUDIO_DIR, name)


def generate_espeak(sentence):
    audio_filepath = unique_filepath('wav')
    text_filepath = unique_filepath('txt')

    with open(text_filepath, 'w') as f:
        f.write(sentence.encode('utf8'))

    cmd = ['espeak', '-v', 'fr-fr', '-s', '120', '-f', text_filepath, '-w', audio_filepath]
    subprocess.check_call(cmd)

    os.remove(text_filepath)

    return audio_filepath


def merge_files(files, filepath):
    converted_files = [adjust_sampling(f) for f in files]

    cmd = ['sox'] + converted_files + [filepath]
    subprocess.check_call(cmd)

    for filepath in (files + converted_files):
        os.remove(filepath)


def adjust_sampling(filepath):
    converted_filepath = unique_filepath('wav')

    cmd = ['sox', filepath, '-c', '1', '-r', '22050', converted_filepath]
    subprocess.check_call(cmd)

    return converted_filepath
