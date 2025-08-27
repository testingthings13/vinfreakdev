import os
from typing import Optional
from starlette.requests import Request
from sqladmin.authentication import AuthenticationBackend
from itsdangerous import URLSafeSerializer

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-this-secret-key")

class SimpleAuth(AuthenticationBackend):
    def __init__(self, secret_key: Optional[str] = None):
        super().__init__(secret_key=secret_key or ADMIN_SECRET)
        self.signer = URLSafeSerializer(self.secret_key)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            request.session.update({"admin": self.signer.dumps({"u": username})})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("admin")
        if not token:
            return False
        try:
            data = self.signer.loads(token)
            return data.get("u") == ADMIN_USER
        except Exception:
            return False
