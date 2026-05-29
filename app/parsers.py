"""업로드된 이력서 파일에서 일반 텍스트를 추출한다.

지원 포맷: PDF(.pdf), Word(.docx), 일반 텍스트(.txt, .md)
"""

import io

from fastapi import HTTPException

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5MB


def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx(data: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


def _extract_txt(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")


def extract_resume_text(filename: str, data: bytes) -> str:
    """파일명 확장자에 따라 적절한 파서를 골라 텍스트를 추출한다."""
    if not data:
        raise HTTPException(400, "빈 파일입니다.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "파일이 너무 큽니다. (최대 5MB)")

    name = (filename or "").lower()

    try:
        if name.endswith(".pdf"):
            text = _extract_pdf(data)
        elif name.endswith(".docx"):
            text = _extract_docx(data)
        elif name.endswith((".txt", ".md")):
            text = _extract_txt(data)
        else:
            raise HTTPException(
                400,
                f"지원하지 않는 파일 형식입니다. 지원: {', '.join(SUPPORTED_EXTENSIONS)}",
            )
    except HTTPException:
        raise
    except Exception as exc:  # 파싱 라이브러리 내부 오류
        raise HTTPException(422, f"파일에서 텍스트를 추출하지 못했습니다: {exc}")

    text = text.strip()
    if not text:
        raise HTTPException(
            422,
            "파일에서 텍스트를 찾지 못했습니다. (스캔 이미지 PDF일 수 있습니다)",
        )
    return text
