"""Password protection and authorized PDF unlocking."""
from __future__ import annotations

from pathlib import Path

import pikepdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import ValidationError, validate_pdf


def protect_pdf(
    source: str | Path, destination: str | Path, open_password: str, *,
    owner_password: str | None = None, allow_printing: bool = True,
    allow_copying: bool = True, allow_editing: bool = False,
) -> Path:
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve(); ensure_distinct_paths(info.path, output)
    if not open_password: raise ValueError("Open password cannot be empty.")
    if len(open_password.encode("utf-8")) > 127: raise ValueError("Password is too long.")
    owner = owner_password or open_password
    permissions = pikepdf.Permissions(
        accessibility=allow_copying, extract=allow_copying,
        print_lowres=allow_printing, print_highres=allow_printing,
        modify_annotation=allow_editing, modify_assembly=allow_editing,
        modify_form=allow_editing, modify_other=allow_editing,
    )
    encryption = pikepdf.Encryption(owner=owner, user=open_password, R=6, allow=permissions, aes=True, metadata=True)
    try:
        with pikepdf.open(info.path) as document, atomic_output(output) as temporary:
            document.save(temporary, encryption=encryption)
    except pikepdf.PasswordError as exc:
        raise ValidationError("The source PDF is already protected.") from exc
    return output


def unlock_pdf(source: str | Path, destination: str | Path, password: str) -> Path:
    info = validate_pdf(source, allow_encrypted=True)
    output = Path(destination).expanduser().resolve(); ensure_distinct_paths(info.path, output)
    if not info.encrypted: raise ValidationError("The selected PDF is not password protected.")
    if not password: raise ValueError("Enter the PDF password.")
    try:
        with pikepdf.open(info.path, password=password) as document, atomic_output(output) as temporary:
            document.save(temporary)
    except pikepdf.PasswordError as exc:
        raise ValidationError("The PDF password is incorrect.") from exc
    return output


def password_strength(password: str) -> tuple[int, str]:
    """Return a deterministic local-only password score and label."""
    score = min(40, len(password) * 4)
    score += 15 if any(char.islower() for char in password) else 0
    score += 15 if any(char.isupper() for char in password) else 0
    score += 15 if any(char.isdigit() for char in password) else 0
    score += 15 if any(not char.isalnum() for char in password) else 0
    score = min(100, score)
    label = "Weak" if score < 45 else "Fair" if score < 70 else "Strong"
    return score, label
