"""블로그 콘텐츠 처리 유틸 테스트"""

from app.services.blog.content import process_content


class TestProcessContent:
    def test_extracts_toc_from_h2_h3(self):
        html = '<h2 id="intro">소개</h2><p>본문</p><h3 id="detail">상세</h3>'
        result = process_content(html)
        assert result.toc == [
            {"level": "two", "text": "소개", "slug": "intro"},
            {"level": "three", "text": "상세", "slug": "detail"},
        ]

    def test_injects_id_when_missing(self):
        html = "<h2>My Heading</h2>"
        result = process_content(html)
        assert result.toc[0]["slug"] == "my-heading"
        assert 'id="my-heading"' in result.content_html

    def test_korean_heading_id(self):
        html = "<h2>시작하기</h2>"
        result = process_content(html)
        assert result.toc[0]["slug"] == "시작하기"
        assert 'id="시작하기"' in result.content_html

    def test_duplicate_headings_get_unique_ids(self):
        html = "<h2>Setup</h2><h2>Setup</h2>"
        result = process_content(html)
        slugs = [t["slug"] for t in result.toc]
        assert slugs == ["setup", "setup-1"]

    def test_existing_ids_preserved(self):
        html = '<h2 id="custom-id">제목</h2>'
        result = process_content(html)
        assert result.toc[0]["slug"] == "custom-id"
        assert result.content_html == html

    def test_style_and_h1_ignored_in_toc(self):
        html = "<style>.post-body h2 { color: red; }</style><h1>타이틀</h1><h2>섹션</h2>"
        result = process_content(html)
        assert len(result.toc) == 1
        assert result.toc[0]["text"] == "섹션"

    def test_reading_time_minimum_one_minute(self):
        result = process_content("<p>짧은 글</p>")
        assert result.reading_time_minutes == 1

    def test_reading_time_scales_with_length(self):
        long_text = "<p>" + ("word " * 1000) + "</p>"
        result = process_content(long_text)
        assert result.reading_time_minutes == 5  # 1000 words / 200 wpm
