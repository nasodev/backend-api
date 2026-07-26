"""Blog Posts API 통합 테스트 (공개 엔드포인트)"""


class TestPublicPosts:
    def test_list_empty(self, client_with_fake_blog_service):
        response = client_with_fake_blog_service.get("/blog/posts")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_excludes_unpublished(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("published-post")
        fake_blog_service.add_post("draft-post", is_published=False)
        response = client_with_fake_blog_service.get("/blog/posts")
        slugs = [p["slug"] for p in response.json()]
        assert slugs == ["published-post"]

    def test_list_summary_has_no_content_html(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("a-post")
        body = client_with_fake_blog_service.get("/blog/posts").json()
        assert "content_html" not in body[0]
        assert body[0]["title"] == "제목"

    def test_list_filter_by_tag(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("tagged", tags=["nextjs"])
        fake_blog_service.add_post("other", tags=["python"])
        body = client_with_fake_blog_service.get("/blog/posts?tag=nextjs").json()
        assert [p["slug"] for p in body] == ["tagged"]

    def test_detail_returns_content_and_toc(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("my-post", content_html='<h2 id="s">섹션</h2>')
        body = client_with_fake_blog_service.get("/blog/posts/my-post").json()
        assert body["content_html"] == '<h2 id="s">섹션</h2>'
        assert body["toc"] == [{"level": "two", "text": "섹션", "slug": "s"}]

    def test_detail_unpublished_404(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("draft", is_published=False)
        response = client_with_fake_blog_service.get("/blog/posts/draft")
        assert response.status_code == 404

    def test_detail_missing_404(self, client_with_fake_blog_service):
        response = client_with_fake_blog_service.get("/blog/posts/nope")
        assert response.status_code == 404

    def test_view_increments(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("viewed")
        r1 = client_with_fake_blog_service.post("/blog/posts/viewed/view")
        r2 = client_with_fake_blog_service.post("/blog/posts/viewed/view")
        assert r1.json() == {"view_count": 1}
        assert r2.json() == {"view_count": 2}

    def test_view_missing_404(self, client_with_fake_blog_service):
        response = client_with_fake_blog_service.post("/blog/posts/nope/view")
        assert response.status_code == 404
