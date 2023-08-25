import os
import tempfile
from collections import namedtuple
from pathlib import Path

import gradio.components
from PIL import PngImagePlugin

from modules import shared

Savedfile = namedtuple("Savedfile", ["name"])  # TODO: replace by typed NamedTuple


def register_tmp_file(gradio, filename):
    if hasattr(gradio, "temp_file_sets"):  # gradio 3.15
        gradio.temp_file_sets[0] = gradio.temp_file_sets[0] | {Path(filename).resolve()}

    if hasattr(gradio, "temp_dirs"):  # gradio 3.9
        gradio.temp_dirs = gradio.temp_dirs | {Path(filename).parent.resolve()}


def check_tmp_file(gradio, filename):
    if hasattr(gradio, "temp_file_sets"):
        return any(filename in fileset for fileset in gradio.temp_file_sets)

    if hasattr(gradio, "temp_dirs"):
        return any(
            Path(temp_dir).resolve() in Path(filename).resolve().parents
            for temp_dir in gradio.temp_dirs
        )

    return False


def save_pil_to_file(self, pil_image, dir=None, format="png"):
    already_saved_as = getattr(pil_image, "already_saved_as", None)
    if already_saved_as and Path(already_saved_as).is_file():
        register_tmp_file(shared.demo, already_saved_as)
        filename = already_saved_as

        if not shared.opts.save_images_add_number:
            filename += f"?{Path(already_saved_as).stat().st_mtime}"

        return filename

    if shared.opts.temp_dir != "":
        dir = shared.opts.temp_dir
    else:
        Path(dir).mkdir(parents=True, exist_ok=True)

    use_metadata = False
    metadata = PngImagePlugin.PngInfo()
    for key, value in pil_image.info.items():
        if isinstance(key, str) and isinstance(value, str):
            metadata.add_text(key, value)
            use_metadata = True

    file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=dir)
    pil_image.save(file_obj, pnginfo=(metadata if use_metadata else None))
    return file_obj.name


def install_ui_tempdir_override():
    """override save to file function so that it also writes PNG info"""
    gradio.components.IOComponent.pil_to_temp_file = save_pil_to_file


def on_tmpdir_changed():
    if shared.opts.temp_dir == "" or shared.demo is None:
        return

    Path(shared.opts.temp_dir).mkdir(parents=True, exist_ok=True)

    register_tmp_file(shared.demo, Path(shared.opts.temp_dir, "x"))


def cleanup_tmpdr():
    temp_dir = shared.opts.temp_dir
    if temp_dir == "" or not Path(temp_dir).is_dir():
        return

    for root, _, files in os.walk(temp_dir, topdown=False):
        for name in files:
            extension = Path(name).suffix
            if extension != ".png":
                continue

            filename = Path(root, name)
            Path(filename).unlink()
