"""블로그 콘텐츠 처리 — TOC 추출, 제목 id 부여, 리딩타임 계산 (순수 함수)"""

import math
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

WORDS_PER_MINUTE = 200


@dataclass
class ProcessedContent:
    content_html: str
    toc: list[dict]
    reading_time_minutes: int


def _slugify(text: str) -> str:
    """github-slugger 규칙 근사: 소문자화, 공백→하이픈, 유니코드 문자 보존"""
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s가-힣-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"\s+", "-", slug)
    return slug or "section"


def process_content(html: str) -> ProcessedContent:
    soup = BeautifulSoup(html, "html.parser")

    toc: list[dict] = []
    used_ids: dict[str, int] = {}
    changed = False

    for heading in soup.find_all(["h2", "h3"]):
        # <style> 내부 텍스트는 find_all 대상이 아니므로 별도 처리 불필요
        text = heading.get_text(strip=True)
        heading_id = heading.get("id")
        if not heading_id:
            base = _slugify(text)
            count = used_ids.get(base, 0)
            heading_id = base if count == 0 else f"{base}-{count}"
            used_ids[base] = count + 1
            heading["id"] = heading_id
            changed = True
        else:
            used_ids.setdefault(heading_id, 1)
        toc.append({
            "level": "two" if heading.name == "h2" else "three",
            "text": text,
            "slug": heading_id,
        })

    # id 미부여 시 원본 그대로 반환 (불필요한 재직렬화로 인한 포맷 변형 방지)
    content_html = str(soup) if changed else html

    for style in soup.find_all("style"):
        style.decompose()
    plain_text = soup.get_text(separator=" ", strip=True)
    word_count = len(plain_text.split())
    reading_time = max(1, math.ceil(word_count / WORDS_PER_MINUTE))

    return ProcessedContent(
        content_html=content_html,
        toc=toc,
        reading_time_minutes=reading_time,
    )
