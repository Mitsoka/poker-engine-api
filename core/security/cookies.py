from core.config import settings


class CookieManager:
    @staticmethod
    def set_access(res, token: str):
        res.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXP * 60,
            samesite="lax",
            secure=False,
            path="/"
        )

    @staticmethod
    def set_refresh(res, token: str):
        res.set_cookie(
            key="refresh_token",
            value=token,
            httponly=True,
            max_age=settings.REFRESH_TOKEN_EXP * 24 * 60 * 60,
            samesite="lax",
            secure=False,
            path="/"
        )

    @staticmethod
    def set_all(res, access: str, refresh: str):
        CookieManager.set_access(res, access)
        CookieManager.set_refresh(res, refresh)

    @staticmethod
    def delete_all(res):
        res.delete_cookie("access_token")
        res.delete_cookie("refresh_token")