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

    def test_view_unpublished_404(self, client_with_fake_blog_service, fake_blog_service):
        fake_blog_service.add_post("draft", is_published=False)
        response = client_with_fake_blog_service.post("/blog/posts/draft/view")
        assert response.status_code == 404


class TestAdminPosts:
    def test_create_requires_auth(self, client):
        response = client.post("/blog/posts", json={})
        assert response.status_code == 403  # HTTPBearer가 자격 증명 없음 거부

    def test_create_success(self, client_with_fake_blog_admin):
        response = client_with_fake_blog_admin.post(
            "/blog/posts",
            json={
                "slug": "new-post",
                "title": "새 글",
                "description": "설명",
                "content_html": "<h2>섹션</h2><p>본문</p>",
                "tags": ["test"],
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["slug"] == "new-post"
        assert body["toc"] == [{"level": "two", "text": "섹션", "slug": "섹션"}]

    def test_create_duplicate_slug_409(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("existing")
        response = client_with_fake_blog_admin.post(
            "/blog/posts",
            json={"slug": "existing", "title": "t", "description": "d", "content_html": "<p>x</p>"},
        )
        assert response.status_code == 409

    def test_create_invalid_slug_422(self, client_with_fake_blog_admin):
        response = client_with_fake_blog_admin.post(
            "/blog/posts",
            json={"slug": "Invalid Slug!", "title": "t", "description": "d", "content_html": "<p>x</p>"},
        )
        assert response.status_code == 422

    def test_update_success(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("target")
        response = client_with_fake_blog_admin.put(
            "/blog/posts/target", json={"title": "수정된 제목"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "수정된 제목"

    def test_update_content_recomputes_toc(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("target")
        response = client_with_fake_blog_admin.put(
            "/blog/posts/target", json={"content_html": '<h2 id="new">새 섹션</h2>'}
        )
        assert response.json()["toc"] == [{"level": "two", "text": "새 섹션", "slug": "new"}]

    def test_update_missing_404(self, client_with_fake_blog_admin):
        response = client_with_fake_blog_admin.put("/blog/posts/nope", json={"title": "x"})
        assert response.status_code == 404

    def test_update_explicit_null_rejected_422(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("target")
        response = client_with_fake_blog_admin.put(
            "/blog/posts/target", json={"title": None}
        )
        assert response.status_code == 422

    def test_update_cover_image_null_allowed(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("target")
        response = client_with_fake_blog_admin.put(
            "/blog/posts/target", json={"cover_image_url": None}
        )
        assert response.status_code == 200

    def test_delete_success(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("doomed")
        response = client_with_fake_blog_admin.delete("/blog/posts/doomed")
        assert response.status_code == 204
        assert "doomed" not in fake_blog_service.posts

    def test_admin_list_includes_unpublished(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("pub")
        fake_blog_service.add_post("draft", is_published=False)
        response = client_with_fake_blog_admin.get("/blog/admin/posts")
        slugs = {p["slug"] for p in response.json()}
        assert slugs == {"pub", "draft"}

    def test_admin_list_requires_auth(self, client):
        response = client.get("/blog/admin/posts")
        assert response.status_code == 403

    def test_admin_detail_includes_unpublished(self, client_with_fake_blog_admin, fake_blog_service):
        fake_blog_service.add_post("draft", is_published=False)
        response = client_with_fake_blog_admin.get("/blog/admin/posts/draft")
        assert response.status_code == 200
        assert response.json()["slug"] == "draft"
        assert "content_html" in response.json()

    def test_admin_detail_requires_auth(self, client):
        response = client.get("/blog/admin/posts/any")
        assert response.status_code == 403
