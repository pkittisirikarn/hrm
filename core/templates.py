# core/templates.py
from fastapi.templating import Jinja2Templates
from modules.security.perms import has_perm as _has_perm, is_admin_session as _is_admin

templates = Jinja2Templates(directory="templates")
templates.env.globals["has_perm"] = _has_perm
templates.env.globals["is_admin"] = _is_admin
