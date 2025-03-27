# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contains some convenience tools"""

from io import BytesIO
from typing import Optional

from PIL import Image, ImageOps

__all__ = [
    "process_thumbnail",
]


def process_thumbnail(
    input_path: str,
    output_path: Optional[str] = None,
    max_size_kb: int = 200,
) -> None:
    """
    This tool is used for compressing an image to fit within Telegram's thumbnail size limit.

    Arguments:
        input_path (str): The path to the image.
        output_path (str, optional): The path which will be used to save the image. Defaults to the
            input_path.
        max_size_kb (int, optional): The size limit in KB. Defaults to ``200``.
    """
    output_path = output_path or input_path
    img = Image.open(input_path)
    img = ImageOps.contain(img, (320, 320))

    # Convert to RGB (some formats like PNG may have alpha)
    img = img.convert("RGB")

    # Compress image iteratively to fit within size limit
    quality = 95
    while True:
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG", quality=quality)
        size_kb = len(img_bytes.getvalue()) / 1024

        if size_kb <= max_size_kb or quality <= 10:
            break  # Stop when within limit or if quality is too low
        quality -= 5  # Reduce quality in steps

    img.save(output_path, format="JPEG", quality=quality)
