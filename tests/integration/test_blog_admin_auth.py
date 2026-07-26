"""블로그 관리자 인증 의존성 테스트"""

import pytest
from fastapi import HTTPException

from app.dependencies.blog_admin import require_blog_admin
from app.dependencies.entities import FirebaseUser


def make_user(uid: str) -> FirebaseUser:
    return FirebaseUser(uid=uid, email="a@b.c", name="t", token_data={"uid": uid})


class TestRequireBlogAdmin:
    def test_admin_uid_passes(self):
        user = make_user("admin-uid")
        result = require_blog_admin(user, admin_uids=["admin-uid"])
        assert result is user

    def test_non_admin_uid_403(self):
        user = make_user("someone-else")
        with pytest.raises(HTTPException) as exc:
            require_blog_admin(user, admin_uids=["admin-uid"])
        assert exc.value.status_code == 403

    def test_empty_admin_list_403(self):
        user = make_user("any")
        with pytest.raises(HTTPException) as exc:
            require_blog_admin(user, admin_uids=[])
        assert exc.value.status_code == 403
